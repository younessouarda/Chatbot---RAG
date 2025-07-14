import { useEffect, useState } from "react";
import { Route, BrowserRouter as Router, Routes, useLocation, useNavigate } from "react-router-dom";
import Accueil from "./components/accueil.jsx";
import Chat from "./components/chat.jsx";
import Login from "./components/login.jsx";
import Register from "./components/register.jsx";

// Composant enveloppant qui gère le switch
function AuthWrapper() {
  const location = useLocation();
  const navigate = useNavigate();
  const [showLogin, setShowLogin] = useState(true);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const mode = params.get("mode");
    if (mode === "register") setShowLogin(false);
    else setShowLogin(true); // default to login
  }, [location.search]);

  const switchToRegister = () => {
    navigate("/auth?mode=register");
  };

  const switchToLogin = () => {
    navigate("/auth?mode=login");
  };

  return showLogin ? (
    <Login onSwitchToRegister={switchToRegister} />
  ) : (
    <Register onSwitchToLogin={switchToLogin} />
  );
}

function App() {
  return (
    <Router>
      <Routes>
        {/* Page d'accueil */}
        <Route path="/" element={<Accueil />} />

        {/* Page auth avec logique de switch */}
        <Route path="/auth" element={<AuthWrapper />} />

        {/* Page de chat */}
        <Route path="/chat" element={<Chat />} />
      </Routes>
    </Router>
  );
}

export default App;
