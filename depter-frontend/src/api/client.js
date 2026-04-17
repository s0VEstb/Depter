/**
 * Depter API Client
 * Все запросы к FastAPI backend (http://localhost:8000)
 */
import axios from 'axios';

const API_BASE = 'http://localhost:8000';

const api = axios.create({
    baseURL: API_BASE,
    headers: {
        'Content-Type': 'application/json',
    },
});

/**
 * Регистрация нового пользователя
 * POST /api/users
 */
export async function registerUser(userData) {
    const response = await api.post('/api/users', userData);
    return response.data;
}

/**
 * Загрузка PDF-файлов для скоринга
 * POST /api/upload (multipart/form-data)
 * @param {File[]} files — массив PDF-файлов (1–3)
 * @param {string} phone — телефон зарегистрированного пользователя
 * @param {string} [name] — имя (опционально)
 */
export async function uploadFiles(files, phone, name) {
    const formData = new FormData();
    files.forEach((file) => {
        formData.append('files', file);
    });
    formData.append('phone', phone);
    if (name) {
        formData.append('name', name);
    }

    const response = await api.post('/api/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
}

/**
 * Получение статуса обработки (для поллинга)
 * GET /api/status/{job_id}
 */
export async function getJobStatus(jobId) {
    const response = await api.get(`/api/status/${jobId}`);
    return response.data;
}

/**
 * Получение результата скоринга
 * GET /api/profile/{profile_id}
 */
export async function getProfile(profileId) {
    const response = await api.get(`/api/profile/${profileId}`);
    return response.data;
}

/**
 * Авторизация пользователя
 * POST /api/auth/login
 * @param {string} email
 * @param {string} password
 */
export async function loginUser(email, password) {
    const response = await api.post('/api/auth/login', { email, password });
    return response.data;
}

/**
 * История скоринговых профилей пользователя
 * GET /api/users/{user_id}/profiles
 */
export async function getUserProfiles(userId) {
    const response = await api.get(`/api/users/${userId}/profiles`);
    return response.data;
}

export default api;
