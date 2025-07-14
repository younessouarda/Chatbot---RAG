import { useState } from "react";
import { Link } from "react-router-dom";
import "./Auth.css";

export default function Register({ onSwitchToLogin }) {
  // États locaux pour stocker les valeurs des champs du formulaire d'inscription
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  // Fonction appelée lors de la soumission du formulaire d'inscription
  const handleRegister = async (e) => {
    e.preventDefault(); // Empêche le rechargement de la page

    // Vérifie que les mots de passe correspondent avant d'envoyer la requête
    if (password !== confirmPassword) {
      alert("Les mots de passe ne correspondent pas !");
      return; // Stop la fonction si les mots de passe ne correspondent pas
    }

    try {
      // Envoi d'une requête POST pour créer un nouvel utilisateur
      const res = await fetch("http://localhost:5000/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        // Envoie les données nécessaires pour l'inscription
        body: JSON.stringify({ email, username, password }),
      });

      // Récupère la réponse au format JSON
      const data = await res.json();

      if (res.ok) {
        // Si inscription réussie, affiche un message et bascule vers la page de connexion
        alert("Inscription réussie !");
        onSwitchToLogin();
      } else {
        // En cas d'erreur serveur, affiche un message d'erreur
        alert(data.error || "Erreur d'inscription");
      }
    } catch (error) {
      // En cas d'erreur réseau ou autre, affiche une alerte et log l'erreur
      alert("Erreur lors de l'inscription");
      console.error(error);
    }
  };

  return (
    <div className="auth-page">
      {/* Logo cliquable renvoyant à la page d'accueil */}
      <Link to="/" className="brand-name-top">
        <span className="chat-white">Chat</span>
        <span className="rag-blue">RAG</span>
      </Link>

      <div className="auth-container">
        <h2>Inscription</h2>
        {/* Formulaire d'inscription */}
        <form onSubmit={handleRegister} className="auth-form">
          <input
            type="text"
            placeholder="Nom d'utilisateur"
            value={username}
            onChange={(e) => setUsername(e.target.value)} // Met à jour l'état username à chaque saisie
            required
            autoFocus
            pattern="^[a-zA-Z0-9_]{3,20}$" // Validation du format du nom d'utilisateur (lettres, chiffres, underscore, 3 à 20 caractères)
            title="Nom d'utilisateur"
          />

          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)} // Met à jour l'état email à chaque saisie
            required
          />
          <input
            type="password"
            placeholder="Mot de passe"
            value={password}
            onChange={(e) => setPassword(e.target.value)} // Met à jour l'état password à chaque saisie
            required
          />
          <input
            type="password"
            placeholder="Confirmer le mot de passe"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)} // Met à jour l'état confirmPassword à chaque saisie
            required
          />
          <button type="submit">S'inscrire</button>
        </form>
        <div className="auth-links">
          {/* Lien pour basculer vers la page de connexion */}
          <span className="link-btn" onClick={onSwitchToLogin}>
            Déjà inscrit ? Se connecter
          </span>
        </div>
      </div>
    </div>
  );
}
