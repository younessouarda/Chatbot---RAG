import psycopg2
import datetime
import os
from psycopg2.extras import RealDictCursor 

# Configuration de la base de données PostgreSQL
PG_PASSWORD = os.getenv("PG_PASSWORD")

DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": PG_PASSWORD,
    "host": "127.0.0.1",
    "port": "5432"
}


def get_db_connection():
    """Établit une nouvelle connexion à la base de données."""
    return psycopg2.connect(**DB_CONFIG)


def save_conversation(user_id, conversation_id, user_message, bot_response):
    """
    Enregistre un message dans l'historique de la conversation dans la base de données.
    Si c'est le premier message de la conversation, met automatiquement à jour son titre
    en se basant sur un extrait du message utilisateur.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.datetime.now()
    try:
        # Vérifie s’il s’agit du premier message pour cette conversation
        cursor.execute("""
            SELECT COUNT(*) FROM conversation_history
            WHERE conversation_id = %s;
        """, (conversation_id,))
        message_count = cursor.fetchone()[0]

        if message_count == 0:
            # Premier message : définit un titre par défaut à partir du message utilisateur
            titre_extrait = user_message[:50]  # 50 premiers caractères
            if len(user_message) > 50:
                titre_extrait += "..."  # Ajoute "..." si tronqué

            cursor.execute("""
                UPDATE conversations
                SET title = %s
                WHERE id = %s AND user_id = %s;
            """, (titre_extrait, conversation_id, user_id))
            conn.commit()
            print(f"Titre de la conversation {conversation_id} mis à jour : '{titre_extrait}'")

        # Insère le message dans l'historique
        cursor.execute("""
            INSERT INTO conversation_history (user_id, user_message, bot_response, timestamp, conversation_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, user_message, bot_response, timestamp, conversation_id))
        conn.commit()
        print(f"Historique de la conversation {conversation_id} sauvegardé.")

    except Exception as e:
        conn.rollback()
        print(f"Erreur lors de la sauvegarde de la conversation : {e}")
    finally:
        cursor.close()
        conn.close()


def get_conversation_history(user_id, conversation_id):
    """
    Récupère l’historique des échanges (messages utilisateur et réponses du bot)
    pour une conversation donnée appartenant à l'utilisateur.
    """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT user_message, bot_response, timestamp
            FROM conversation_history
            WHERE user_id = %s AND conversation_id = %s
            ORDER BY timestamp ASC
        """, (user_id, conversation_id))
        return cursor.fetchall()
    except Exception as e:
        print(f"Erreur lors de la récupération de l'historique : {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def get_all_conversations_for_user(user_id):
    """
    Récupère la liste des conversations d’un utilisateur, 
    avec leur identifiant et leur titre, triées par date de création décroissante.
    """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT id AS conversation_id, title 
            FROM conversations
            WHERE user_id = %s
            ORDER BY created_at DESC;
        """, (user_id,))
        return cursor.fetchall()
    except Exception as e:
        print(f"Erreur lors de la récupération des conversations pour l'utilisateur {user_id} : {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def create_new_conversation(user_id):
    """
    Crée une nouvelle conversation pour un utilisateur donné 
    avec un titre par défaut. Retourne l’identifiant de la conversation.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO conversations (user_id, title) 
            VALUES (%s, %s) 
            RETURNING id;
        """, (user_id, "Nouvelle Conversation"))
        new_conv_id = cursor.fetchone()[0]
        conn.commit()
        return new_conv_id
    except Exception as e:
        conn.rollback()
        print(f"Erreur lors de la création d'une nouvelle conversation : {e}")
        return None
    finally:
        cursor.close()
        conn.close()


def rename_conversation(conversation_id, new_title, user_id):
    """
    Renomme le titre d’une conversation, en vérifiant qu’elle appartient bien à l’utilisateur.
    Retourne True si la mise à jour a été effectuée, False sinon.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE conversations
            SET title = %s
            WHERE id = %s AND user_id = %s;
        """, (new_title, conversation_id, user_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        conn.rollback()
        print(f"Erreur lors du renommage de la conversation {conversation_id} : {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def delete_conversation(conversation_id, user_id):
    """
    Supprime une conversation et son historique associé (via ON DELETE CASCADE),
    après avoir vérifié qu’elle appartient à l’utilisateur.
    Retourne True si la suppression a réussi, False sinon.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            DELETE FROM conversations
            WHERE id = %s AND user_id = %s;
        """, (conversation_id, user_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        conn.rollback()
        print(f"Erreur lors de la suppression de la conversation {conversation_id} : {e}")
        return False
    finally:
        cursor.close()
        conn.close()
