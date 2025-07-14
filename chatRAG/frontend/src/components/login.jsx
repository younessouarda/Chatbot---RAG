import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import "./Auth.css";

export default function Login({ onSwitchToRegister }) {
  // États locaux pour stocker l'email et le mot de passe saisis par l'utilisateur
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  // Hook pour naviguer vers une autre route après connexion réussie
  const navigate = useNavigate();

  // Fonction appelée lors de la soumission du formulaire de connexion
  const handleLogin = async (e) => {
    e.preventDefault(); // Empêche le rechargement de la page

    try {
      // Envoi d'une requête POST vers le serveur pour authentifier l'utilisateur
      const res = await fetch("http://localhost:5000/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        // Envoie les données email et mot de passe en JSON
        body: JSON.stringify({ email, password }),
      });

      // Récupère la réponse au format JSON
      const data = await res.json();

      if (res.ok) {
        // Si connexion réussie, stocke le token d'authentification dans localStorage
        localStorage.setItem("authToken", data.access_token);
        // Redirige l'utilisateur vers la page du chat
        navigate("/chat");
      } else {
        // En cas d'erreur, affiche un message d'alerte avec l'erreur reçue ou un message générique
        alert(data.error || "Erreur de connexion");
      }
    } catch (error) {
      // En cas d'erreur réseau ou autre, affiche une alerte et log l'erreur en console
      alert("Erreur lors de la connexion");
      console.error(error);
    }
  };

  // Fonction simulant l'envoi d'un lien de réinitialisation de mot de passe
  const handleForgotPassword = () => {
    alert("Un lien de réinitialisation a été envoyé à votre adresse email (simulation).");
  };

  return (
    <div className="auth-page">
      {/* Logo cliquable renvoyant à la page d'accueil */}
      <Link to="/" className="brand-name-top">
        <span className="chat-white">Chat</span>
        <span className="rag-blue">RAG</span>
      </Link>

      <div className="auth-container">
        <h2>Connexion</h2>
        {/* Formulaire de connexion */}
        <form onSubmit={handleLogin} className="auth-form">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)} // Met à jour l'état email à chaque saisie
            required
            autoFocus
          />
          <input
            type="password"
            placeholder="Mot de passe"
            value={password}
            onChange={(e) => setPassword(e.target.value)} // Met à jour l'état mot de passe à chaque saisie
            required
          />
          <button type="submit">Se connecter</button>
        </form>

        <div className="auth-links">
          {/* Lien pour mot de passe oublié (simulation) */}
          <span className="link-btn" onClick={handleForgotPassword}>
            Mot de passe oublié ?
          </span>
          {/* Lien pour basculer vers le formulaire d'inscription */}
          <span className="link-btn" onClick={onSwitchToRegister}>
            Créer un compte
          </span>
        </div>
      </div>
    </div>
  );
}
