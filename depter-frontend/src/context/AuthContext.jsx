import { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

/**
 * AuthProvider — контекст авторизации через localStorage
 * При регистрации данные пользователя сохраняются и доступны везде
 */
export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);

    useEffect(() => {
        // Читаем из localStorage при загрузке
        const stored = localStorage.getItem('depter_user');
        if (stored) {
            try {
                setUser(JSON.parse(stored));
            } catch {
                // невалидный JSON — очищаем
                localStorage.removeItem('depter_user');
            }
        }
    }, []);

    const login = (userData) => {
        localStorage.setItem('depter_user', JSON.stringify(userData));
        setUser(userData);
    };

    const logout = () => {
        localStorage.removeItem('depter_user');
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export const useAuth = () => useContext(AuthContext);
