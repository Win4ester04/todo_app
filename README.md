# ToDo App (FastAPI + Next.js + SQLite)

# Установка и запуск

### Backend (FastAPI)

1. Перейдите в папку `backend`:
   cd backend

2. Создайте и активируйте виртуальное окружение
   python -m venv venv
   venv\Scripts\activate

3. Установите зависимости
   pip install -r requirements.txt

4. Запустите сервер
   uvicorn main:app --reload

### Frontend (Next.js)

1. Перейдите в папку frontend
   cd frontend

2. Установите зависимости
   npm install

3. Запустите сервер
   npm run dev

### Примеры запросов

1. Регистрация

POST http://localhost:8000/register/
Content-Type: application/json

{
"username": "testuser",
"password": "123456",
"email": "test@example.com",
"full_name": "Test User"
}

2. Авторизация

POST http://localhost:8000/token
Content-Type: application/x-www-form-urlencoded

username=testuser&password=123456

3. Создание поста

POST http://localhost:8000/posts/
Authorization: Bearer jwt_token
Content-Type: application/json

{
"title": "My Task",
"description": "Do something",
"completed": false
}
