import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Chat.css"; // Ce fichier CSS  contient les styles nécessaires

export default function Chat() {

  // --- Variables d'état ---
  const navigate = useNavigate();

  // Gestion des conversations
  const [conversations, setConversations] = useState([]);
  const [selectedConvId, setSelectedConvId] = useState(null);
  const [messages, setMessages] = useState({}); // Stocke les messages pour chaque conversation_id
  const [showConvOptionsId, setShowConvOptionsId] = useState(null); // ID de la conversation dont on affiche les options

  // Saisie et génération de réponse du chat
  const [input, setInput] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isGeneratingResponse, setIsGeneratingResponse] = useState(false);

  // Sélection du modèle et téléchargement
  const [agentType, setAgentType] = useState("local");
  const [selectedModel, setSelectedModel] = useState("");
  // const [availableModels, setAvailableModels] = useState([]);
  const [isSelectedModelDownloaded, setIsSelectedModelDownloaded] = useState(true); // Le modèle local sélectionné est-il téléchargé ?
  const [isDownloadingModel, setIsDownloadingModel] = useState(false); // Indique si un téléchargement est en cours
  const [downloadProgress, setDownloadProgress] = useState({}); // {nom_du_modèle: {downloaded_bytes: X, total_bytes: Y, status: 'downloading'|'completed'|'failed'|'cancelled'}}
  const [isCancellingDownload, setIsCancellingDownload] = useState(false); // État pour la gestion de l'annulation du téléchargement
  const [showDownloadFinishedMessage, setShowDownloadFinishedMessage] = useState(false); // État temporaire pour afficher un message "téléchargement terminé"

  const [modelsList, setModelsList] = useState([]);

  // État de l'interface utilisateur
  const [showUserMenu, setShowUserMenu] = useState(false);

  // --- Références ---
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null); // Permet de faire défiler automatiquement les messages vers le bas
  const convOptionsMenuRef = useRef(null); // Référence pour le menu des options de conversation (pour détecter clics en dehors)
  const downloadPollingIntervalRef = useRef(null); // Référence pour l'intervalle de polling du téléchargement

  // --- Helpers pour appels API ---

  /**
   * Récupère les messages pour une conversation donnée
   * @param {string|null} convId - ID de la conversation
   */
  const fetchMessagesForConversation = useCallback(async (convId) => {
    if (convId === null) return;

    console.log("Fetching messages for conversation ID:", convId);
    const token = localStorage.getItem("authToken");
    console.log("Token for conversation history fetch:", token ? "Token present" : "Token missing");

    // Vide les messages pour cette conversation avant de recharger
    setMessages((prev) => ({
      ...prev,
      [convId]: [],
    }));

    try {
      const response = await fetch(`http://localhost:5000/conversation_history/${convId}`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error("HTTP Error fetching messages:", response.status, errorData);
        throw new Error(errorData.error || `HTTP error! Status: ${response.status}`);
      }

      const data = await response.json();
      setMessages((prev) => ({
        ...prev,
        [convId]: data,
      }));
    } catch (error) {
      console.error(`Erreur lors du chargement des messages pour la conversation ${convId} :`, error);
      setMessages((prev) => ({
        ...prev,
        [convId]: [{ from: "bot", text: "Erreur lors du chargement de l'historique de la conversation." }],
      }));
    }
  }, []); // Pas de dépendances, fonction stable

  /**
   * Crée une nouvelle conversation via l'API
   * @returns {Promise<object|null>} - Nouvelle conversation ou null en cas d'erreur
   */
  const createNewConversation = useCallback(async () => {
    try {
      const token = localStorage.getItem("authToken");
      const response = await fetch("http://localhost:5000/new_conversation", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Erreur lors de la création d'une nouvelle conversation :", error);
      return null;
    }
  }, []); // Pas de dépendances

  /**
   * Récupère la liste des conversations via l'API et gère la sélection automatique
   */
  const fetchConversations = useCallback(async () => {
    try {
      const token = localStorage.getItem("authToken");
      if (!token) {
        console.error("Aucun token trouvé dans le localStorage.");
        return;
      }

      const response = await fetch("http://localhost:5000/conversations", {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error("Erreur HTTP:", response.status);
        console.error("Réponse erreur :", errorText);
        if (response.status === 401) {
          localStorage.removeItem("authToken");
          navigate("/");
          alert("Votre session a expiré. Veuillez vous reconnecter.");
        }
        return;
      }

      const data = await response.json();
      console.log("Conversations récupérées :", data);
      setConversations(data);

      let newSelectedConvId = null;

      if (data.length > 0) {
        // Vérifie si la conversation sélectionnée est toujours dans la liste
        const currentSelectedStillExists = data.some((conv) => conv.conversation_id === selectedConvId);
        if (selectedConvId !== null && currentSelectedStillExists) {
          newSelectedConvId = selectedConvId;
        } else {
          newSelectedConvId = data[0].conversation_id;
        }
      } else {
        // Si aucune conversation existante, en créer une nouvelle
        const newConv = await createNewConversation();
        if (newConv) {
          setConversations([newConv]);
          newSelectedConvId = newConv.conversation_id;
        }
      }

      // Met à jour la conversation sélectionnée seulement si elle a changé
      if (newSelectedConvId !== selectedConvId) {
        setSelectedConvId(newSelectedConvId);
      } else if (newSelectedConvId !== null && !messages[newSelectedConvId]) {
        // Si sélection non modifiée mais messages non chargés, les récupérer
        fetchMessagesForConversation(newSelectedConvId);
      }
    } catch (error) {
      console.error("Erreur lors du chargement des conversations :", error);
    }
  }, [selectedConvId, createNewConversation, fetchMessagesForConversation, navigate, messages]);


  // --- Logique de polling pour suivi du téléchargement ---

  /**
   * Vérifie régulièrement l'état du téléchargement du modèle
   * @param {string} modelName - Nom du modèle à vérifier
   */
  const pollDownloadProgress = useCallback(async (modelName) => {
    const token = localStorage.getItem("authToken");
    if (!token) {
      console.error("Aucun token trouvé. Impossible de suivre le progrès du téléchargement.");
      stopPolling();
      setIsDownloadingModel(false); // Réinitialise l'état de téléchargement
      return;
    }

    try {
      const response = await fetch(`http://localhost:5000/check_model_downloaded/${modelName}`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (response.ok) {
        const data = await response.json();
        console.log(`[Polling] ${modelName} | Status: ${data.status} | Downloaded: ${formatBytes(data.downloaded_bytes)} / Total: ${formatBytes(data.total_bytes)}`);

        setDownloadProgress((prev) => ({
          ...prev,
          [modelName]: {
            downloaded_bytes: data.downloaded_bytes,
            total_bytes: data.total_bytes,
            status: data.status,
          },
        }));

        setIsSelectedModelDownloaded(data.downloaded);

        if (data.status === 'downloading') {
          setIsDownloadingModel(true);
          setShowDownloadFinishedMessage(false);
        } else if (data.status === 'completed') {
          console.log(`Download of ${modelName} completed.`);
          setIsDownloadingModel(false);
          setIsSelectedModelDownloaded(true);
          stopPolling();
          setShowDownloadFinishedMessage(true);
          setTimeout(() => {
            setShowDownloadFinishedMessage(false);
          }, 3000); // Cache le message après 3 secondes
        } else if (data.status === 'failed' || data.status === 'cancelled') {
          console.log(`Download of ${modelName} ${data.status}.`);
          setIsDownloadingModel(false);
          setIsSelectedModelDownloaded(false);
          stopPolling();
          setShowDownloadFinishedMessage(false);
        } else {
          setIsDownloadingModel(false);
          setShowDownloadFinishedMessage(false);
        }
      } else {
        console.error("Erreur lors de la récupération du progrès:", response.status);
        stopPolling();
        setIsDownloadingModel(false);
        setShowDownloadFinishedMessage(false);
      }
    } catch (error) {
      console.error("Erreur réseau lors de la récupération du progrès:", error);
      stopPolling();
      setIsDownloadingModel(false);
      setShowDownloadFinishedMessage(false);
    }
  }, []);

  /**
   * Démarre le polling périodique pour le suivi du téléchargement
   * @param {string} modelName - Nom du modèle à surveiller
   */
  const startPolling = useCallback((modelName) => {
    if (downloadPollingIntervalRef.current) {
      clearInterval(downloadPollingIntervalRef.current);
    }
    downloadPollingIntervalRef.current = setInterval(() => pollDownloadProgress(modelName), 1500);
    pollDownloadProgress(modelName); // Appel initial immédiat
  }, [pollDownloadProgress]);

  /**
   * Arrête le polling périodique
   */
  const stopPolling = useCallback(() => {
    if (downloadPollingIntervalRef.current) {
      clearInterval(downloadPollingIntervalRef.current);
      downloadPollingIntervalRef.current = null;
    }
  }, []);

  // --- Gestionnaires d'événements ---

  /**
   * Création d'une nouvelle conversation et mise à jour de l'état
   */
  const handleNewConversation = async () => {
    const newConv = await createNewConversation();
    if (newConv) {
      setConversations((prev) => [newConv, ...prev]);
      setSelectedConvId(newConv.conversation_id);
      setMessages((prev) => ({
        ...prev,
        [newConv.conversation_id]: [],
      }));
    }
  };


  /**
   * Envoi d'un message utilisateur au backend et gestion des réponses
   */
  const handleSend = async () => {
    if (!input.trim() || selectedConvId === null) return;
    const userMessage = input.trim();

    // Récupération du token JWT
    const token = localStorage.getItem("authToken");
    if (!token) {
      console.error("Token JWT non trouvé.");
      setMessages((prev) => {
        const updatedMessages = (prev[selectedConvId] || []).filter(
          (msg) => !(msg.from === "bot" && msg.isAnimated)
        );
        return {
          ...prev,
          [selectedConvId]: [
            ...updatedMessages,
            { from: "bot", text: "Veuillez vous connecter pour envoyer un message." },
          ],
        };
      });
      setIsGeneratingResponse(false);
      return;
    }

    // Utilisation directe de l'ID du modèle sélectionné
    const modelId = selectedModel;

    if (!modelId) {
      setMessages((prev) => ({
        ...prev,
        [selectedConvId]: [
          ...(prev[selectedConvId] || []),
          { from: "bot", text: `Aucun modèle sélectionné.` },
        ],
      }));
      setIsGeneratingResponse(false);
      return;
    }

    // Ajout du message utilisateur à la conversation
    setMessages((prev) => ({
      ...prev,
      [selectedConvId]: [...(prev[selectedConvId] || []), { from: "user", text: userMessage }],
    }));
    setInput("");

    // Affiche un message d'attente animé
    setIsGeneratingResponse(true);
    setMessages((prev) => ({
      ...prev,
      [selectedConvId]: [
        ...(prev[selectedConvId] || []),
        { from: "bot", text: "Veuillez patienter", isAnimated: true },
      ],
    }));

    try {
      const response = await fetch("http://localhost:5000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          question: userMessage,
          agent_type: agentType,
          model_name: modelId, // Utilise l'ID réel du modèle
          conversation_id: selectedConvId,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error("HTTP Error lors du chat:", response.status, errorData);
        throw new Error(errorData.error || `Erreur HTTP: ${response.status}`);
      }

      const data = await response.json();

      // Supprime le message animé avant d'ajouter la réponse réelle du bot
      setMessages((prev) => {
        const updatedMessages = (prev[selectedConvId] || []).filter(
          (msg) => !(msg.from === "bot" && msg.isAnimated)
        );
        return {
          ...prev,
          [selectedConvId]: [...updatedMessages, { from: "bot", text: data.reponse }],
        };
      });

      // Met à jour le titre de la conversation si elle est encore "Nouvelle Conversation"
      setConversations((prevConvs) =>
        prevConvs.map((conv) =>
          conv.conversation_id === selectedConvId && conv.title === "Nouvelle Conversation"
            ? {
                ...conv,
                title:
                  userMessage.substring(0, 50) +
                  (userMessage.length > 50 ? "..." : ""),
              }
            : conv
        )
      );
    } catch (error) {
      // Supprime le message animé et affiche le message d'erreur dans la conversation
      setMessages((prev) => {
        const updatedMessages = (prev[selectedConvId] || []).filter(
          (msg) => !(msg.from === "bot" && msg.isAnimated)
        );
        return {
          ...prev,
          [selectedConvId]: [
            ...updatedMessages,
            {
              from: "bot",
              text: `Erreur lors de la communication avec le serveur: ${error.message || 'Erreur inconnue'}`,
            },
          ],
        };
      });
      console.error("Erreur backend:", error);
    } finally {
      setIsGeneratingResponse(false);
    }
  };








  const handleFileChange = async (e) => {
    // Récupère la liste des fichiers sélectionnés dans l'input file
    const files = e.target.files;

    // Vérifie si des fichiers sont sélectionnés et si une conversation est sélectionnée
    if (!files.length || selectedConvId === null) {
      console.log("No files selected or no conversation selected. Aborting upload.");
      return; // Arrête la fonction si aucune condition n'est remplie
    }

    // Récupère le token d'authentification depuis le localStorage
    const token = localStorage.getItem("authToken");
    
    // Si aucun token n'est trouvé, avertir l'utilisateur et arrêter
    if (!token) {
      alert("Please log in to upload documents.");
      console.error("Attempted file upload without token.");
      return;
    }

    // Indique que le téléchargement est en cours (pour gérer l'UI par exemple)
    setIsUploading(true);

    // Crée un objet FormData pour envoyer les fichiers via une requête POST
    const formData = new FormData();
    // Ajoute chaque fichier dans le FormData sous la clé 'file'
    for (let i = 0; i < files.length; i++) {
      formData.append('file', files[i]);
      console.log(`Appending file to FormData: ${files[i].name}`);
    }

    // Met à jour les messages pour indiquer que le traitement est en cours
    setMessages((prev) => ({
      ...prev,
      [selectedConvId]: [
        // On filtre les anciens messages animés du bot pour éviter les doublons
        ...(prev[selectedConvId] || []).filter((msg) => !(msg.from === "bot" && msg.isAnimated)),
        { from: "bot", text: "Traitement des documents en cours", isAnimated: true },
      ],
    }));

    console.log(`Sending upload request to: http://localhost:5000/upload_document/${selectedConvId}`);

    try {
      // Envoie la requête POST au backend avec le FormData et le token d'auth
      const response = await fetch(`http://localhost:5000/upload_document/${selectedConvId}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,  // Ajoute le token dans l'entête Authorization
        },
        body: formData, // Envoie les fichiers
      });

      // Si la réponse HTTP n'est pas OK (ex: 4xx, 5xx)
      if (!response.ok) {
        console.error(`HTTP error! Status: ${response.status}`);
        let errorDetails = `HTTP Error ${response.status}`;
        try {
          // Essaye d'extraire un message d'erreur JSON plus précis
          const errorJson = await response.json();
          errorDetails = errorJson.error || errorJson.message || JSON.stringify(errorJson);
        } catch (jsonError) {
          // Si ce n'est pas un JSON, récupère le texte brut
          errorDetails = await response.text();
        }
        // Lève une erreur avec les détails pour gérer ça dans le catch
        throw new Error(`Upload failed: ${errorDetails}`);
      }

      // Parse la réponse JSON (succès)
      const data = await response.json();
      console.log("Upload successful response:", data);

      // Met à jour les messages avec la réponse du serveur, en supprimant le message "Traitement en cours"
      setMessages((prev) => {
        const updatedMessages = (prev[selectedConvId] || []).filter(
          (msg) => !(msg.from === "bot" && msg.isAnimated) // Suppression du message animé temporaire
        );
        return {
          ...prev,
          [selectedConvId]: [
            ...updatedMessages,
            { from: "bot", text: response.ok ? data.message : `Erreur d'upload: ${data.error || 'Erreur inconnue'}` },
          ],
        };
      });
    } catch (error) {
      // Gestion des erreurs réseau ou levées précédemment
      console.error("Erreur lors de l'upload du fichier (frontend catch) :", error);
      setMessages((prev) => {
        const updatedMessages = (prev[selectedConvId] || []).filter(
          (msg) => !(msg.from === "bot" && msg.isAnimated)
        );
        return {
          ...prev,
          [selectedConvId]: [
            ...updatedMessages,
            { from: "bot", text: `Erreur lors de l'upload: ${error.message || 'Erreur de connexion inconnue'}` },
          ],
        };
      });
    } finally {
      // Finalement, on arrête l'indicateur de chargement et on vide la sélection du fichier
      setIsUploading(false);
      e.target.value = null; // Reset de l'input file pour permettre re-sélection du même fichier si besoin
    }
  };


  const handleUserMenuClick = (option) => {
    // Gestion des actions du menu utilisateur selon l'option choisie
    if (option === "parametres") {
      alert("Ouverture des paramètres (non implémenté pour l'instant).");
    } else if (option === "deconnexion") {
      // Suppression du token pour déconnexion
      localStorage.removeItem("authToken");
      // Réinitialise la liste des conversations et messages, ainsi que la conversation sélectionnée
      setConversations([]);
      setMessages({});
      setSelectedConvId(null);
      alert("Déconnexion réussie !");
      // Redirige vers la page d'accueil (login par exemple)
      navigate("/");
    }
    // Cache le menu utilisateur après le clic
    setShowUserMenu(false);
  };

  const handleRenameConversation = async (convId, currentTitle) => {
    setShowConvOptionsId(null); // Cache les options de conversation

    // Demande à l'utilisateur un nouveau titre via un prompt
    const newTitle = prompt("Renommer la conversation:", currentTitle);

    // Vérifie si le titre a changé et n'est pas vide
    if (newTitle !== null && newTitle.trim() !== currentTitle) {
      // Récupère le token d'authentification
      const token = localStorage.getItem("authToken");
      if (!token) {
        alert("Vous devez être connecté pour renommer une conversation.");
        return;
      }

      try {
        // Envoie la requête PUT au backend pour changer le titre de la conversation
        const response = await fetch(`http://localhost:5000/rename_conversation/${convId}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ new_title: newTitle.trim() }),
        });

        if (response.ok) {
          // Mise à jour locale des conversations avec le nouveau titre
          setConversations((prevConvs) =>
            prevConvs.map((conv) =>
              conv.conversation_id === convId ? { ...conv, title: newTitle.trim() } : conv
            )
          );
        } else {
          // Gestion des erreurs serveur
          const errorData = await response.json().catch(() => ({ error: "Erreur inconnue" }));
          console.error("Erreur lors du renommage de la conversation:", errorData.error);
          alert(`Impossible de renommer la conversation: ${errorData.error || 'Erreur serveur.'}`);
        }
      } catch (error) {
        // Erreur réseau
        console.error("Erreur réseau lors du renommage:", error);
        alert("Erreur réseau lors du renommage de la conversation.");
      }
    }
  };

  const handleDeleteConversation = async (convId) => {
    setShowConvOptionsId(null); // Cache les options de conversation

    // Demande confirmation à l'utilisateur avant suppression
    if (window.confirm("Êtes-vous sûr de vouloir supprimer cette conversation ? Cette action est irréversible.")) {
      // Récupère le token d'authentification
      const token = localStorage.getItem("authToken");
      if (!token) {
        alert("Vous devez être connecté pour supprimer une conversation.");
        return;
      }

      try {
        // Envoie la requête DELETE au backend pour supprimer la conversation
        const response = await fetch(`http://localhost:5000/delete_conversation/${convId}`, {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.ok) {
          // Met à jour la liste locale en retirant la conversation supprimée
          setConversations((prevConvs) =>
            prevConvs.filter((conv) => conv.conversation_id !== convId)
          );

          // Supprime aussi les messages liés à cette conversation
          setMessages((prevMessages) => {
            const newMessages = { ...prevMessages };
            delete newMessages[convId];
            return newMessages;
          });

          // Si la conversation supprimée est sélectionnée, la désélectionne et recharge la liste des conversations
          if (selectedConvId === convId) {
            setSelectedConvId(null);
            await fetchConversations();
          }
        } else {
          // Gestion des erreurs serveur
          const errorData = await response.json().catch(() => ({ error: "Erreur inconnue" }));
          console.error("Erreur lors de la suppression de la conversation:", errorData.error);
          alert(`Impossible de supprimer la conversation: ${errorData.error || 'Erreur serveur.'}`);
        }
      } catch (error) {
        // Erreur réseau
        console.error("Erreur réseau lors de la suppression:", error);
        alert("Erreur réseau lors de la suppression de la conversation.");
      }
    }
  };


  const handleDownloadModel = async () => {
    setIsDownloadingModel(true);      // Indique que le téléchargement est en cours
    setIsCancellingDownload(false);   // Réinitialise l'état d'annulation
    setShowDownloadFinishedMessage(false); // Cache le message de fin de téléchargement

    // Initialise la progression du téléchargement dans l'UI
    setDownloadProgress(prev => ({
      ...prev,
      [selectedModel]: {
        ...prev[selectedModel],
        status: 'downloading',
        downloaded_bytes: prev[selectedModel]?.downloaded_bytes || 0,
        total_bytes: modelsList.find(m => m.value === selectedModel)?.size_mb * 1024 * 1024 || 0
      }
    }));

    startPolling(selectedModel); // Démarre un poll pour vérifier la progression

    try {
      const token = localStorage.getItem("authToken");
      if (!token) {
        throw new Error("Token JWT non trouvé. Impossible de télécharger le modèle.");
      }

      // Envoie une requête POST pour démarrer le téléchargement du modèle
      const response = await fetch(`http://localhost:5000/download_model/${selectedModel}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (response.ok || response.status === 202) {
        const data = await response.json();
        if (data.message.includes("déjà téléchargé")) {
          // Si le modèle est déjà téléchargé, met à jour l'état en conséquence
          setIsSelectedModelDownloaded(true);
          setIsDownloadingModel(false);
          stopPolling();
          setShowDownloadFinishedMessage(true);
          // Cache le message après 3 secondes
          setTimeout(() => setShowDownloadFinishedMessage(false), 3000);
        } else {
          console.log(`Téléchargement de ${selectedModel} initié.`);
        }
      } else {
        // Gestion des erreurs serveur
        const errorData = await response.json();
        throw new Error(errorData.error || `Erreur lors du téléchargement: ${response.status}`);
      }
    } catch (error) {
      // Gestion des erreurs réseau ou levées précédemment
      console.error("Erreur lors du téléchargement du modèle (API call):", error);
      setDownloadProgress(prev => ({
        ...prev,
        [selectedModel]: { ...prev[selectedModel], status: 'failed' }
      }));
      setIsSelectedModelDownloaded(false);
      stopPolling();
      setIsDownloadingModel(false);
      setShowDownloadFinishedMessage(false);
    }
  };


  const handleCancelDownload = async () => {
    setIsCancellingDownload(true); // Indique que l'annulation est en cours
    setDownloadProgress(prev => ({
      ...prev,
      [selectedModel]: { ...prev[selectedModel], status: 'cancelling' }
    }));
    setShowDownloadFinishedMessage(false);

    try {
      const token = localStorage.getItem("authToken");
      if (!token) {
        throw new Error("Token JWT non trouvé. Impossible d'annuler le téléchargement.");
      }

      // Envoie une requête POST pour annuler le téléchargement du modèle
      const response = await fetch(`http://localhost:5000/cancel_download/${selectedModel}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (response.ok || response.status === 202) {
        const data = await response.json();
        console.log(data.message);
      } else {
        // Gestion des erreurs serveur
        const errorData = await response.json();
        throw new Error(errorData.error || `Erreur lors de l'annulation: ${response.status}`);
      }
    } catch (error) {
      // Gestion des erreurs réseau ou levées précédemment
      console.error("Erreur lors de l'annulation du téléchargement (API call):", error);
      setDownloadProgress(prev => ({
        ...prev,
        [selectedModel]: { ...prev[selectedModel], status: 'failed' }
      }));
    } finally {
      setIsCancellingDownload(false); // Fin de l'état d'annulation
    }
  };


  // --- Effets ---

  // Effet pour faire défiler automatiquement la liste des messages vers le bas
  useEffect(() => {
    // Quand les messages ou la conversation sélectionnée changent,
    // on fait défiler la vue jusqu'à la fin pour voir les derniers messages
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, selectedConvId]);

  // Effet pour charger la liste des conversations au montage du composant
  useEffect(() => {
    // Appelle la fonction fetchConversations une seule fois au démarrage
    fetchConversations();
  }, [fetchConversations]);

  // Effet pour récupérer les messages quand la conversation sélectionnée change
  useEffect(() => {
    // Charge les messages correspondant à la conversation sélectionnée
    fetchMessagesForConversation(selectedConvId);
  }, [selectedConvId, fetchMessagesForConversation]);

  // Effet pour charger la liste des modèles disponibles en fonction du type d'agent,
  // et vérifier l'état de téléchargement des modèles locaux
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const token = localStorage.getItem("authToken");
        if (!token) {
          console.error("Aucun token trouvé. Impossible de charger les modèles.");
          return;
        }

        // Requête API pour récupérer les modèles selon agentType (local ou en ligne)
        const response = await fetch(`http://localhost:5000/models?agent_type=${agentType}`, {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        });

        if (!response.ok) {
          const errorData = await response.json();
          console.error("Erreur HTTP lors du chargement des modèles:", response.status, errorData);
          throw new Error(errorData.error || `Erreur HTTP! Statut: ${response.status}`);
        }

        const data = await response.json();

        // Pour les modèles en ligne, on vérifie que la valeur est une URL et on ajoute api_url
        const updatedModels = data.map((model) => {
          if (agentType === "enligne") {
            const matched = model.value && model.value.startsWith("http");
            return {
              ...model,
              api_url: matched ? model.value : null,
            };
          }
          // Pour les modèles locaux, on retourne tels quels
          return model;
        });

        // Mise à jour de la liste des modèles dans le state
        setModelsList(updatedModels);

        if (updatedModels.length > 0) {
          // Sélection du premier modèle par défaut
          const initialModel = updatedModels[0].value;
          setSelectedModel(initialModel);

          if (agentType === "local") {
            // Si local, on récupère les infos de téléchargement du modèle initial
            const firstModelInfo = updatedModels.find((m) => m.value === initialModel);
            if (firstModelInfo) {
              // On détermine le statut de téléchargement (terminé, en cours, non téléchargé)
              const status = firstModelInfo.status || (firstModelInfo.downloaded ? "completed" : "not_downloaded");
              setDownloadProgress((prev) => ({
                ...prev,
                [firstModelInfo.value]: {
                  downloaded_bytes: firstModelInfo.downloaded_bytes || 0,
                  total_bytes: firstModelInfo.size_mb ? firstModelInfo.size_mb * 1024 * 1024 : 0,
                  status: status,
                },
              }));
              // Si le modèle est en cours de téléchargement, on démarre le polling
              if (status === "downloading") {
                startPolling(firstModelInfo.value);
                setIsDownloadingModel(true);
              } else {
                // Sinon on met à jour l'état de disponibilité et fin du téléchargement
                setIsSelectedModelDownloaded(firstModelInfo.downloaded);
                setIsDownloadingModel(false);
              }
            } else {
              // Si pas d'info sur le modèle, on met l'état par défaut
              setIsSelectedModelDownloaded(false);
              setIsDownloadingModel(false);
              stopPolling();
            }
          } else {
            // Pour les modèles en ligne, on considère toujours qu'ils sont disponibles
            setIsSelectedModelDownloaded(true);
            setIsDownloadingModel(false);
          }
        } else {
          // Si aucun modèle disponible, on réinitialise les sélections
          setSelectedModel("");
          setIsSelectedModelDownloaded(true);
          setIsDownloadingModel(false);
        }

        // Cache le message de fin de téléchargement si affiché précédemment
        setShowDownloadFinishedMessage(false);
      } catch (error) {
        // En cas d'erreur lors du chargement des modèles, on réinitialise les états
        console.error("Erreur de chargement des modèles :", error);
        setModelsList([]);
        setSelectedModel("");
        setIsSelectedModelDownloaded(true);
        setIsDownloadingModel(false);
        setShowDownloadFinishedMessage(false);
      }
    };

    // Lance la fonction asynchrone pour récupérer les modèles
    fetchModels();
  }, [agentType, startPolling, stopPolling]);

  // Effet pour gérer le polling (rafraîchissement automatique) en fonction de l'état de téléchargement
  useEffect(() => {
    // Recherche les infos du modèle sélectionné dans la liste
    const modelInfo = modelsList.find(m => m.value === selectedModel);
    // Récupère le statut actuel du téléchargement pour ce modèle
    const currentModelProgressStatus = downloadProgress[selectedModel]?.status;

    if (agentType === "local" && selectedModel) {
      if (currentModelProgressStatus === 'downloading') {
        // Si en cours de téléchargement, on lance le polling et active le flag téléchargement
        startPolling(selectedModel);
        setIsDownloadingModel(true);
      } else if (modelInfo?.downloaded || currentModelProgressStatus === 'completed') {
        // Si le modèle est téléchargé, on met à jour les états et stoppe le polling
        setIsSelectedModelDownloaded(true);
        setIsDownloadingModel(false);
        stopPolling();
      } else {
        // Sinon, pas en cours ni téléchargé, on met à jour les états et stoppe le polling
        setIsSelectedModelDownloaded(false);
        setIsDownloadingModel(false);
        stopPolling();
      }
    } else {
      // Pour agent en ligne ou aucun modèle sélectionné, on considère le modèle disponible et stoppe polling
      setIsSelectedModelDownloaded(true);
      setIsDownloadingModel(false);
      stopPolling();
    }

    // Cache le message de fin téléchargement lors d'un changement de modèle ou de type d'agent
    setShowDownloadFinishedMessage(false);

    // Nettoyage à la désactivation ou changement de dépendances : arrête le polling
    return () => stopPolling();
  }, [agentType, selectedModel, modelsList, downloadProgress, startPolling, stopPolling]);

  // Effet pour fermer les menus déroulants lorsque l'utilisateur clique en dehors
  useEffect(() => {
    const handleClickOutside = (e) => {
      // Si clic en dehors du bouton utilisateur ou du menu utilisateur, on ferme le menu utilisateur
      if (
        !e.target.closest(".user-icon-button") &&
        !e.target.closest(".user-dropdown")
      ) {
        setShowUserMenu(false);
      }
      // Si clic en dehors du bouton options conversation ou menu options, on ferme ce menu
      if (
        !e.target.closest(".conversation-options-button") &&
        !e.target.closest(".conversation-options-dropdown")
      ) {
        setShowConvOptionsId(null);
      }
    };

    // Ajoute l'écouteur d'événement sur le document pour détecter clics hors menus
    document.addEventListener("click", handleClickOutside);

    // Nettoyage à la destruction du composant : suppression de l'écouteur
    return () => document.removeEventListener("click", handleClickOutside);
  }, []);








  // --- Variables de logique d'affichage ---

// Récupère l'état de progression du téléchargement du modèle sélectionné
const currentModelProgress = downloadProgress[selectedModel];
// Récupère le statut actuel du modèle (ex : 'downloading', 'completed', etc.)
const modelStatus = currentModelProgress?.status;
// Booléens pour simplifier les conditions d'affichage selon le statut du modèle
const isModelDownloading = modelStatus === 'downloading';
const isModelCompleted = modelStatus === 'completed';
const isModelFailed = modelStatus === 'failed';
const isModelCancelled = modelStatus === 'cancelled';

// Récupère le nom du modèle sélectionné dans la liste des modèles, ou affiche la valeur brute si non trouvée
const modelNameDisplay = modelsList.find(m => m.value === selectedModel)?.name || selectedModel;

return (
  <div className="chat-container">
    {/* Colonne de gauche : liste des conversations */}
    <div className="conversations-list">
      <h3>Conversations</h3>
      <button className="new-conversation-btn" onClick={handleNewConversation}>
        + Nouvelle conversation
      </button>
      {/* Affiche chaque conversation */}
      {conversations.map((conv) => (
        <div
          key={conv.conversation_id}
          className={`conversation-item ${conv.conversation_id === selectedConvId ? "selected" : ""}`}
          onClick={() => {
            // Si on clique sur une conversation différente, on la sélectionne
            if (selectedConvId !== conv.conversation_id) {
              setSelectedConvId(conv.conversation_id);
            }
            // Ferme le menu d'options des conversations
            setShowConvOptionsId(null);
          }}
        >
          <span className="conversation-title">{conv.title}</span>
          {/* Options pour chaque conversation (renommer, supprimer) */}
          <div className={`conversation-options-container ${showConvOptionsId === conv.conversation_id ? 'active-dropdown' : ''}`}>
            <button
              className="conversation-options-button"
              onClick={(e) => {
                // Empêche la propagation du clic pour éviter de changer la conversation
                e.stopPropagation();
                // Affiche ou cache le menu options de cette conversation
                setShowConvOptionsId(showConvOptionsId === conv.conversation_id ? null : conv.conversation_id);
              }}
              aria-label="Options de conversation"
            >
              ...
            </button>
            {showConvOptionsId === conv.conversation_id && (
              <div className="conversation-options-dropdown" ref={convOptionsMenuRef}>
                <button onClick={() => handleRenameConversation(conv.conversation_id, conv.title)}>
                  🖉 Renommer
                </button>
                <button onClick={() => handleDeleteConversation(conv.conversation_id)}>
                  ✖ Supprimer
                </button>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>

    {/* Zone principale de chat */}
    <div className="chat-main">
      <header className="chat-header">
        <div className="model-options">
          {/* Choix du type d'agent : local ou en ligne */}
          <select value={agentType} onChange={(e) => setAgentType(e.target.value)}>
            <option value="local">🖥️ Génération locale</option>
            <option value="enligne">🌐 Génération en ligne</option>
          </select>

          {/* Sélecteur de modèle parmi la liste */}
          <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)}>
            {modelsList.map((model, idx) => (
              <option key={idx} value={model.value}>
                {model.name}
              </option>
            ))}
          </select>

          {/* Affichage de l'état de téléchargement pour les modèles locaux */}
          {agentType === "local" && selectedModel && (
            <div className="download-status-container">
              {isModelDownloading ? (
                // Affiche la progression du téléchargement avec bouton d'annulation
                <div className="download-text-display">
                  <span className="download-text">
                    Téléchargement de **{modelNameDisplay}** en cours
                    <span className="typing-animation"><span>.</span><span>.</span><span>.</span></span>
                  </span>
                  <button
                    onClick={handleCancelDownload}
                    disabled={isCancellingDownload}
                    className="cancel-download-btn"
                  >
                    {isCancellingDownload ? "Annulation..." : "Annuler"}
                  </button>
                </div>
              ) : isSelectedModelDownloaded && isModelCompleted && showDownloadFinishedMessage ? (
                // Message temporaire indiquant que le modèle est téléchargé
                <span className="model-status-message completed-status temporary-message">
                  **{modelNameDisplay} téléchargé !**
                </span>
              ) : isModelFailed ? (
                // Message d'erreur si le téléchargement a échoué
                <span className="model-status-message failed-status">
                  Téléchargement de {modelNameDisplay} échoué
                </span>
              ) : isModelCancelled ? (
                // Message indiquant que le téléchargement a été annulé
                <span className="model-status-message cancelled-status">
                  Téléchargement de {modelNameDisplay} annulé
                </span>
              ) : (
                // Bouton de téléchargement si modèle non téléchargé et pas en cours de téléchargement
                !isSelectedModelDownloaded && (
                  <div className="download-prompt-header">
                    <span>{modelNameDisplay} n'est pas téléchargé.</span>
                    <button onClick={handleDownloadModel} disabled={isDownloadingModel}>
                      Télécharger
                    </button>
                  </div>
                )
              )}
            </div>
          )}
        </div>

        {/* Menu utilisateur avec bouton et options */}
        <div className="user-menu-container">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="user-icon-button"
            aria-label="Paramètres utilisateur"
          >
            <img
              src="https://cdn-icons-png.flaticon.com/512/1946/1946429.png"
              alt="User Icon"
            />
          </button>

          {showUserMenu && (
            <div className="user-dropdown">
              <button onClick={() => handleUserMenuClick("parametres")}>
                ⚙️ Paramètres
              </button>
              <button onClick={() => handleUserMenuClick("deconnexion")}>
                ➨ Déconnexion
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Zone d'affichage des messages */}
      <div className="messages">
        {(messages[selectedConvId] || []).map((msg, i) => (
          <div
            key={i}
            className={msg.from === "user" ? "message-user" : "message-bot"}
          >
            {msg.isAnimated ? (
              <>
                {msg.text}
                <span className="typing-animation">
                  <span>.</span><span>.</span><span>.</span>
                </span>
              </>
            ) : (
              msg.text
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Zone de saisie du message */}
      <div className="input-area">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          style={{ display: "none" }}
          multiple
        />
        <button
          onClick={() => fileInputRef.current.click()}
          disabled={isUploading}
          className="upload-btn"
        >
          📎
        </button>

        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === "Enter" && handleSend()}
          placeholder={isUploading ? "Chargement des documents..." : "Envoyez un message..."}
          disabled={
            isUploading ||
            isGeneratingResponse ||
            (agentType === "local" &&
              (!isSelectedModelDownloaded || isModelDownloading || isModelCancelled || isModelFailed))
          }
        />
        <button
          onClick={handleSend}
          className="send-btn"
          disabled={
            !input.trim() ||
            isGeneratingResponse ||
            (agentType === "local" &&
              (!isSelectedModelDownloaded || isModelDownloading || isModelCancelled || isModelFailed))
          }
        >
          Envoyer
        </button>
      </div>
    </div>
  </div>
);
}