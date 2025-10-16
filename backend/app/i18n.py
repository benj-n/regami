"""
Internationalization support for the Regami API.
Detects language from Accept-Language header and provides localized messages.
"""
from typing import Dict, Optional
from fastapi import Request
import re


# Translation dictionaries
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        # Auth errors
        "invalid_credentials": "Invalid email or password",
        "email_already_registered": "This email is already registered",
        "token_expired": "Your session has expired. Please log in again",
        "token_invalid": "Invalid authentication token",
        "unauthorized": "Authentication required",

        # Validation errors
        "validation_error": "Validation error",
        "required_field": "This field is required",
        "invalid_email": "Invalid email address",
        "password_too_short": "Password must be at least 6 characters",
        "invalid_date": "Invalid date format",

        # Dog profile errors
        "dog_not_found": "Dog profile not found",
        "dog_already_exists": "A dog profile with this name already exists",
        "unauthorized_dog_access": "You don't have permission to access this dog profile",

        # Availability errors
        "availability_not_found": "Availability not found",
        "availability_conflict": "This time slot conflicts with existing availability",
        "past_date_error": "Cannot create availability in the past",

        # Notification messages
        "new_match": "New match found for {dog_name}!",
        "offer_accepted": "Your offer has been accepted",
        "offer_declined": "Your offer has been declined",
        "request_accepted": "Your request has been accepted",
        "request_declined": "Your request has been declined",

        # Success messages
        "registration_success": "Registration successful! Welcome to Regami",
        "profile_updated": "Profile updated successfully",
        "dog_created": "Dog profile created successfully",
        "dog_updated": "Dog profile updated successfully",
        "dog_deleted": "Dog profile deleted successfully",
        "availability_created": "Availability created successfully",
        "availability_updated": "Availability updated successfully",
        "availability_deleted": "Availability deleted successfully",

        # Email subjects
        "email_welcome_subject": "Welcome to Regami!",
        "email_match_subject": "New match for {dog_name}",
        "email_offer_subject": "Offer status update",

        # General
        "server_error": "An error occurred. Please try again later",
        "not_found": "Resource not found",
        "forbidden": "You don't have permission to perform this action",
    },
    "fr": {
        # Auth errors
        "invalid_credentials": "Email ou mot de passe invalide",
        "email_already_registered": "Cet email est déjà enregistré",
        "token_expired": "Votre session a expiré. Veuillez vous reconnecter",
        "token_invalid": "Jeton d'authentification invalide",
        "unauthorized": "Authentification requise",

        # Validation errors
        "validation_error": "Erreur de validation",
        "required_field": "Ce champ est requis",
        "invalid_email": "Adresse email invalide",
        "password_too_short": "Le mot de passe doit contenir au moins 6 caractères",
        "invalid_date": "Format de date invalide",

        # Dog profile errors
        "dog_not_found": "Profil de chien introuvable",
        "dog_already_exists": "Un profil de chien avec ce nom existe déjà",
        "unauthorized_dog_access": "Vous n'avez pas la permission d'accéder à ce profil",

        # Availability errors
        "availability_not_found": "Disponibilité introuvable",
        "availability_conflict": "Ce créneau est en conflit avec une disponibilité existante",
        "past_date_error": "Impossible de créer une disponibilité dans le passé",

        # Notification messages
        "new_match": "Nouveau match trouvé pour {dog_name}!",
        "offer_accepted": "Votre offre a été acceptée",
        "offer_declined": "Votre offre a été refusée",
        "request_accepted": "Votre demande a été acceptée",
        "request_declined": "Votre demande a été refusée",

        # Success messages
        "registration_success": "Inscription réussie! Bienvenue sur Regami",
        "profile_updated": "Profil mis à jour avec succès",
        "dog_created": "Profil de chien créé avec succès",
        "dog_updated": "Profil de chien mis à jour avec succès",
        "dog_deleted": "Profil de chien supprimé avec succès",
        "availability_created": "Disponibilité créée avec succès",
        "availability_updated": "Disponibilité mise à jour avec succès",
        "availability_deleted": "Disponibilité supprimée avec succès",

        # Email subjects
        "email_welcome_subject": "Bienvenue sur Regami!",
        "email_match_subject": "Nouveau match pour {dog_name}",
        "email_offer_subject": "Mise à jour du statut de l'offre",

        # General
        "server_error": "Une erreur est survenue. Veuillez réessayer plus tard",
        "not_found": "Ressource introuvable",
        "forbidden": "Vous n'avez pas la permission d'effectuer cette action",
    }
}

DEFAULT_LANGUAGE = "fr"  # French is primary language


def parse_accept_language(accept_language: Optional[str]) -> str:
    """
    Parse Accept-Language header and return best matching language code.

    Format: Accept-Language: fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7
    Returns: 'fr' or 'en' (defaults to 'fr' if no match)
    """
    if not accept_language:
        return DEFAULT_LANGUAGE

    # Parse language preferences with quality scores
    languages = []
    for lang_spec in accept_language.split(','):
        lang_spec = lang_spec.strip()
        if ';q=' in lang_spec:
            lang, quality = lang_spec.split(';q=')
            try:
                quality_score = float(quality)
            except ValueError:
                quality_score = 1.0
        else:
            lang = lang_spec
            quality_score = 1.0

        # Extract base language code (fr-FR -> fr)
        base_lang = lang.split('-')[0].lower()
        languages.append((base_lang, quality_score))

    # Sort by quality score (descending)
    languages.sort(key=lambda x: x[1], reverse=True)

    # Find first supported language
    for lang_code, _ in languages:
        if lang_code in TRANSLATIONS:
            return lang_code

    return DEFAULT_LANGUAGE


def get_language_from_request(request: Request) -> str:
    """Extract language preference from request headers."""
    accept_language = request.headers.get("Accept-Language")
    return parse_accept_language(accept_language)


def translate(key: str, language: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """
    Get translated message for given key and language.

    Args:
        key: Message key to translate
        language: Language code (en, fr)
        **kwargs: Format parameters for the message

    Returns:
        Translated and formatted message
    """
    lang_dict = TRANSLATIONS.get(language, TRANSLATIONS[DEFAULT_LANGUAGE])
    message = lang_dict.get(key, key)  # Fallback to key if translation missing

    # Format message with provided parameters
    if kwargs:
        try:
            message = message.format(**kwargs)
        except (KeyError, ValueError):
            pass  # Return unformatted message if formatting fails

    return message


def get_translator(request: Request):
    """
    Dependency to get translator function for current request.

    Usage in route:
        @app.get("/example")
        def example(t: Callable = Depends(get_translator)):
            return {"message": t("success_message")}
    """
    language = get_language_from_request(request)

    def t(key: str, **kwargs) -> str:
        return translate(key, language, **kwargs)

    return t
