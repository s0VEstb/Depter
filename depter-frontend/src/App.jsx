import { Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import UploadPage from './pages/UploadPage';
import ProgressPage from './pages/ProgressPage';
import ResultPage from './pages/ResultPage';
import ProfilePage from './pages/ProfilePage';

/**
 * App — Layout + маршруты
 * Navbar присутствует на всех страницах
 */
export default function App() {
  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/progress/:jobId" element={<ProgressPage />} />
        <Route path="/result/:profileId" element={<ResultPage />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Routes>
    </>
  );
}
