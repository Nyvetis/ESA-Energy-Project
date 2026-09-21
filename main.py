from access.access_control import check_access
from database.data import *

print("==============================")
print("         PROGRAMME")
print("==============================")

print(f"UID carte    : {uid_carte}")
print(f"Niveau carte : {niveau_carte}")
print(f"Niveau porte : {niveau_porte}")

print("------------------------------")

if check_access(niveau_carte, niveau_porte):
    print("ACCÈS AUTORISÉ")
else:
    print("ACCÈS REFUSÉ")