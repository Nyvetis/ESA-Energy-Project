/*
 * Workshop Horizon 2080 - Lecteur de porte
 * ESP32-S3-CAM + RC522 + LED verte/rouge + buzzer
 *
 * Bibliothèques à installer (Arduino IDE > Gestionnaire de bibliothèques) :
 *   - MFRC522 (par GithubCommunity)
 *   - ArduinoJson (par Benoit Blanchon, version 7)
 * Carte à sélectionner : "ESP32S3 Dev Module"
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ArduinoJson.h>

// ======================= CONFIGURATION =======================
const char* WIFI_SSID = "NOM_DU_WIFI";
const char* WIFI_PASS = "MOT_DE_PASSE";
const char* API_URL   = "http://192.168.1.10:8000/api/scan";  // IP du PC qui fait tourner l'API
const int   PORTE_ID  = 1;                                    // id de la porte dans la BDD

// ======================= BROCHES =============================
#define RC522_SCK   14
#define RC522_MOSI  21
#define RC522_MISO  47
#define RC522_SS    41
#define RC522_RST   42

#define LED_VERTE   1
#define LED_ROUGE   2
#define BUZZER      3

MFRC522 rfid(RC522_SS, RC522_RST);

// Résultats possibles d'un scan
enum Resultat { AUTORISE, REFUSE, ERREUR };

// ---------------------------------------------------------------
// Convertit l'UID lu en texte hexadécimal, ex : "A1B2C3D4"
// ---------------------------------------------------------------
String lireUID() {
  String uid = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (rfid.uid.uidByte[i] < 0x10) uid += "0";
    uid += String(rfid.uid.uidByte[i], HEX);
  }
  uid.toUpperCase();
  return uid;
}

// ---------------------------------------------------------------
// Signaux lumineux et sonores
// ---------------------------------------------------------------
void bip(int nombre, int duree) {
  for (int i = 0; i < nombre; i++) {
    digitalWrite(BUZZER, HIGH);
    delay(duree);
    digitalWrite(BUZZER, LOW);
    delay(duree);
  }
}

void signalAutorise() {
  digitalWrite(LED_VERTE, HIGH);
  bip(1, 200);
  delay(2000);                 // porte "ouverte" pendant 2 s
  digitalWrite(LED_VERTE, LOW);
}

void signalRefuse() {
  digitalWrite(LED_ROUGE, HIGH);
  bip(3, 100);
  delay(1500);
  digitalWrite(LED_ROUGE, LOW);
}

void signalErreur() {
  // Serveur injoignable : la porte reste fermée (fail-secure)
  for (int i = 0; i < 5; i++) {
    digitalWrite(LED_ROUGE, HIGH);
    delay(150);
    digitalWrite(LED_ROUGE, LOW);
    delay(150);
  }
  bip(1, 600);
}

// ---------------------------------------------------------------
// Envoie l'UID à l'API et récupère la décision
// ---------------------------------------------------------------
Resultat envoyerScan(const String& uid) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi non connecté");
    return ERREUR;
  }

  HTTPClient http;
  http.begin(API_URL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(3000);

  JsonDocument requete;
  requete["uid"] = uid;
  requete["porte_id"] = PORTE_ID;
  String corps;
  serializeJson(requete, corps);

  int code = http.POST(corps);
  if (code != 200) {
    Serial.printf("Erreur HTTP : %d\n", code);
    http.end();
    return ERREUR;
  }

  JsonDocument reponse;
  DeserializationError err = deserializeJson(reponse, http.getString());
  http.end();

  if (err) {
    Serial.println("Réponse JSON invalide");
    return ERREUR;
  }

  bool autorise = reponse["autorise"] | false;
  if (autorise) {
    Serial.printf("Accès autorisé : %s %s\n",
                  reponse["prenom"] | "", reponse["nom"] | "");
    return AUTORISE;
  }

  Serial.printf("Accès refusé : %s\n", reponse["motif"] | "inconnu");
  return REFUSE;
}

// ---------------------------------------------------------------
void connecterWifi() {
  Serial.printf("Connexion à %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  unsigned long debut = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - debut < 10000) {
    delay(500);
    Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\nConnecté, IP : %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\nÉchec de connexion, nouvel essai plus tard");
  }
}

void setup() {
  Serial.begin(115200);

  pinMode(LED_VERTE, OUTPUT);
  pinMode(LED_ROUGE, OUTPUT);
  pinMode(BUZZER, OUTPUT);

  SPI.begin(RC522_SCK, RC522_MISO, RC522_MOSI, RC522_SS);
  rfid.PCD_Init();
  Serial.println("Lecteur RC522 prêt");

  connecterWifi();
  bip(2, 80);  // signal de démarrage
}

void loop() {
  // Reconnexion automatique si le Wi-Fi tombe
  if (WiFi.status() != WL_CONNECTED) {
    connecterWifi();
  }

  // Attente d'un badge
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    return;
  }

  String uid = lireUID();
  Serial.printf("Badge détecté : %s\n", uid.c_str());

  switch (envoyerScan(uid)) {
    case AUTORISE: signalAutorise(); break;
    case REFUSE:   signalRefuse();   break;
    case ERREUR:   signalErreur();   break;
  }

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
  delay(500);  // évite les doubles lectures
}
