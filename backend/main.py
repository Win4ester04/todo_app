from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from models import UserDB, PostDB
from database import session_local, engine, Base
from schemas import User, UserCreate, Token, TokenData, Post, PostCreate, PostUpdate
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

# import secrets
# print(secrets.token_hex(32))


SECRET_KEY = "0ab07f3f9edb3fc718cbaf523f48bed886227a0b11c14abed4d969fcd1d06f16"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


Base.metadata.create_all(bind=engine)

def get_db():
    db = session_local()
    try:
        yield db
    finally:
        db.close()


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")



app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(db: Session, username: str):
    return db.query(UserDB).filter(UserDB.username == username).first()
    

def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)  
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = get_user(db, username=token_data.username) 
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me/", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@app.post("/register/", response_model=User)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(user.password)
    new_user = UserDB(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        disabled=False,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    db.close()
    return new_user


@app.post("/posts/", response_model=Post)
async def create_post(post: PostCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    new_post = PostDB(
        title=post.title,
        description=post.description,
        completed=post.completed,
        author_id=current_user.id
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post


@app.get("/posts/", response_model=list[Post])
async def read_posts(skip: int = 0, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    posts = db.query(PostDB).filter(PostDB.author_id == current_user.id).offset(skip).all()
    return posts


@app.get("/posts/{post_id}", response_model=Post)
async def read_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    post = db.query(PostDB).filter(PostDB.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@app.put("/posts/{post_id}", response_model=Post)
async def update_post(post_id: int, post: PostUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    db_post = db.query(PostDB).filter(PostDB.id == post_id, PostDB.author_id == current_user.id).first()
    if db_post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.title is not None:
        db_post.title = post.title
    if post.description is not None:
        db_post.description = post.description
    if post.completed is not None:
        db_post.completed = post.completed
    db.commit()
    db.refresh(db_post)
    return db_post


@app.delete("/posts/{post_id}")
async def delete_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    db_post = db.query(PostDB).filter(PostDB.id == post_id, PostDB.author_id == current_user.id).first()
    if db_post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    db.delete(db_post)
    db.commit()
    return {"detail": "Post deleted"}


@app.get("/logout/")
async def logout():
    return {"detail": "Logout successful"}


# pwd = get_password_hash("aidar123")
# print(pwd)