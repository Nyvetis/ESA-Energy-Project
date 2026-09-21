def check_access(niveau_carte, niveau_porte):
    """
    Vérifie si le niveau de la carte permet
    d'accéder à la porte.

    Une carte peut accéder à une porte si :
        niveau_carte >= niveau_porte

    Retourne True si l'accès est autorisé,
    sinon False.
    """

    return niveau_carte >= niveau_porte