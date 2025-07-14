import { Link } from "react-router-dom";
import "./accueil.css";

const Accueil = () => {
  return (
    <div className="home-page">
      <div className="main-content-wrapper">
        {/* Section Héros : Présentation principale avec le nom de la marque et un message de bienvenue */}
        <div className="hero-section">
          <h1 className="brand-name">
            <span className="chat-white">Chat</span>
            <span className="rag-blue">RAG</span>
          </h1>
          <p className="welcome-text">
            Bienvenue sur la plateforme intelligente de question-réponse basée sur vos documents.
          </p>
          {/* Boutons pour accéder aux pages de connexion et d'inscription */}
          <div className="auth-buttons">
            <Link to="/auth?mode=login" className="home-btn login-btn">
              Connexion
            </Link>
            <Link to="/auth?mode=register" className="home-btn register-btn">
              Inscription
            </Link>
          </div>
        </div>

        {/* Section Services : Liste des fonctionnalités principales proposées par la plateforme */}
        <div className="features-section section-card">
          <h2>Nos Services</h2>
          <ul>
            <li>Upload sécurisé de vos documents</li>
            <li>Recherche sémantique intelligente</li>
            <li>Réponses générées par des modèles LLM performants</li>
            <li>Historique de conversations structuré</li>
          </ul>
        </div>

        {/* Section Comment ça fonctionne : Explication du fonctionnement général de la plateforme */}
        <div className="how-it-works-section section-card">
          <h2>Comment ça fonctionne ?</h2>
          <p>
            Une fois vos documents importés, le système extrait et indexe automatiquement l’information clé.
            Vous pouvez ensuite poser des questions et recevoir des réponses contextuelles, précises et adaptées à vos documents.
          </p>
        </div>

        {/* Section Types de génération : Description des deux modes de génération disponibles */}
        <div className="generation-mode-section section-card">
          <h2>Types de génération</h2>
          <div className="generation-options">
            <div className="option">
              <h3>Génération en ligne</h3>
              <p>Utilise des modèles cloud puissants pour des réponses rapides. Idéal pour la performance.</p>
            </div>
            <div className="option">
              <h3>Génération locale</h3>
              <p>Permet un traitement confidentiel sur votre propre machine. Parfait pour les données sensibles.</p>
            </div>
          </div>
        </div>
      </div>

      {/* Footer : Pied de page avec les droits d’auteur */}
      <footer className="footer">
        © 2025 ChatRAG — Tous droits réservés.
      </footer>
    </div>
  );
};

export default Accueil;
