# ChatRAG

ChatRAG est une application intelligente de question-réponse basée sur vos propres documents, propulsée par des modèles LLM.  

Elle comprend un **frontend React** (React + Vite) et un **backend Python** (Flask).


---

## Structure du projet

ChatRAG/
├── backend/ # Backend Python (API)
├── frontend/ # Frontend React
├── requirements.txt # Dépendances Python
├── README.md # Ce fichier
└── .gitignore # Fichiers/dossiers exclus du repo



---

##  Installation

### Pour le Backend (Python)

1. **Créer un environnement virtuel :**
    Apres que vous avez ovrit le projet chatrag dans votre IDE
    Dans votre teminal exécuter cette commande: python -m venv venv

2. **Activer l’environnement :**
    Linux/macOS : source venv/bin/activate
    Windows : .\venv\Scripts\activate

3. **Installer les dépendances :**
    Exécuter cette commande qui va utilise le fichier requirements.txt pour installer les dépendances Python:

    pip install -r requirements.txt

4. **Démarrer le serveur backend :**
    
    Pour demarrer le backend tu peut executer le fichier application.py situe dans le chemin suivant " backend\app\rag_multiagents\agents\application.py"


### Pour Frontend (React):

1. **Aller dans le dossier frontend :**

    Dans votre terminal executer cette commande: cd frontend

2. **Installer les dépendances** :

    npm install

3. **Lancer l'application frontend :**

    Executer cette commande : npm run dev

    L'application sera disponible par défaut sur : http://localhost:5173


### Prérequis :

    Python 3.9+

    Node.js 18+ et npm



## Auteur
    Développé par [Youness OUARDA au sein de 3D Smart Factory, Mohammédia, Maroc].

