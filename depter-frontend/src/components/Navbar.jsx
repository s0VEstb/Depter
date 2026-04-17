import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/**
 * Navbar — навигационная панель
 * Присутствует на всех страницах: логотип + ссылки + кнопки авторизации
 */
export default function Navbar() {
    const location = useLocation();
    const navigate = useNavigate();
    const { user, logout } = useAuth();

    const isActive = (path) => location.pathname === path;

    const handleLogout = () => {
        logout();
        navigate('/');
    };

    return (
        <nav className="navbar">
            <div className="navbar-inner">
                {/* Логотип: "D" в градиенте, остальное белое */}
                <Link to="/" className="navbar-logo">
                    <span className="logo-d">D</span>
                    <span className="logo-rest">epter</span>
                </Link>

                <div className="navbar-links">
                    <Link
                        to="/"
                        className={`navbar-link ${isActive('/') ? 'active' : ''}`}
                    >
                        Главная
                    </Link>
                    <Link
                        to="/register"
                        className={`navbar-link ${isActive('/register') ? 'active' : ''}`}
                    >
                        Новый скоринг
                    </Link>
                </div>

                {/* Кнопки авторизации */}
                <div className="nav-auth">
                    {user ? (
                        <>
                            <span className="nav-username">👤 {user.full_name}</span>
                            <button
                                className="btn btn-secondary btn-sm"
                                onClick={() => navigate('/upload')}
                            >
                                Профиль
                            </button>
                            <button
                                className="btn btn-ghost btn-sm"
                                onClick={handleLogout}
                            >
                                Выйти
                            </button>
                        </>
                    ) : (
                        <button
                            className="btn btn-primary btn-sm"
                            onClick={() => navigate('/login')}
                        >
                            Войти
                        </button>
                    )}
                </div>
            </div>
        </nav>
    );
}
