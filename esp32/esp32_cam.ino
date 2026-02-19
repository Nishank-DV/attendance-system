#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <WiFiClient.h>
#include "mbedtls/base64.h"

// =========================
// CONFIGURATION (single place)
// =========================
struct AppConfig {
  const char* wifiSsid = "YOUR_WIFI_SSID";
  const char* wifiPassword = "YOUR_WIFI_PASSWORD";

  // Change only this base URL for backend IP/port.
  const char* backendBaseUrl = "http://192.168.1.100:5000";

  uint32_t modePollIntervalMs = 2000;
  uint32_t captureIntervalMs = 3500;
  uint16_t connectTimeoutMs = 4000;
  uint16_t requestTimeoutMs = 8000;
  uint8_t maxPostRetries = 2;
} cfg;

// =========================
// AI Thinker Pin Map
// =========================
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

#define BUZZER_PIN        12

WebServer server(80);
String currentMode = "idle";
unsigned long lastModePollMs = 0;
unsigned long lastCaptureMs = 0;

String modeUrl;
String recognizeUrl;

void setupCamera();
void connectWiFi();
bool ensureWiFiConnected();
String fetchDeviceMode();
bool captureAndSendToBackend();
bool postFrameAsBase64Json(camera_fb_t* fb, String& responseBody, int& httpCode);
char* allocBuffer(size_t sizeBytes);
bool buildRecognizePayload(const uint8_t* imageData, size_t imageLen, char** outPayload, size_t* outLen);
void handleBuzzer();
void beepPattern(const String& pattern);
String extractJsonString(const String& jsonText, const char* key);

void setup() {
  Serial.begin(115200);
  delay(300);

  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  modeUrl = String(cfg.backendBaseUrl) + "/device_mode";
  recognizeUrl = String(cfg.backendBaseUrl) + "/api/recognize";

  setupCamera();
  connectWiFi();

  server.on("/buzzer", HTTP_POST, handleBuzzer);
  server.on("/health", HTTP_GET, []() {
    String body = "{\"status\":\"ok\",\"service\":\"esp32-cam\",\"mode\":\"" + currentMode + "\"}";
    server.send(200, "application/json", body);
  });
  server.begin();

  Serial.println("ESP32-CAM ready");
  Serial.printf("Backend: %s\n", cfg.backendBaseUrl);
}

void loop() {
  server.handleClient();

  if (!ensureWiFiConnected()) {
    delay(200);
    return;
  }

  const unsigned long nowMs = millis();

  if (nowMs - lastModePollMs >= cfg.modePollIntervalMs) {
    lastModePollMs = nowMs;
    String polledMode = fetchDeviceMode();
    if (polledMode.length() > 0) {
      currentMode = polledMode;
    }
  }

  if (currentMode != "register" && currentMode != "attendance") {
    delay(80);
    return;
  }

  if (nowMs - lastCaptureMs < cfg.captureIntervalMs) {
    delay(20);
    return;
  }

  lastCaptureMs = nowMs;
  captureAndSendToBackend();
}

void setupCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  // Required memory-safe settings.
  config.frame_size = FRAMESIZE_QVGA;
  config.jpeg_quality = 15;
  config.fb_count = 1;

#if defined(CAMERA_GRAB_WHEN_EMPTY)
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
#endif
#if defined(CAMERA_FB_IN_PSRAM)
  config.fb_location = CAMERA_FB_IN_PSRAM;
#endif

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
    beepPattern("error");
    return;
  }

  sensor_t* sensor = esp_camera_sensor_get();
  if (sensor != nullptr) {
    sensor->set_framesize(sensor, FRAMESIZE_QVGA);
    sensor->set_quality(sensor, 15);
    sensor->set_brightness(sensor, 0);
    sensor->set_contrast(sensor, 0);
    sensor->set_saturation(sensor, 0);
  }
}

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(cfg.wifiSsid, cfg.wifiPassword);

  Serial.print("Connecting WiFi");
  uint8_t attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 60) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi connected. IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("WiFi connect timeout. Will retry in loop.");
  }
}

bool ensureWiFiConnected() {
  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }

  static unsigned long lastRetryMs = 0;
  unsigned long nowMs = millis();
  if (nowMs - lastRetryMs < 3000) {
    return false;
  }

  lastRetryMs = nowMs;
  Serial.println("WiFi disconnected. Reconnecting...");
  WiFi.disconnect(true, false);
  WiFi.begin(cfg.wifiSsid, cfg.wifiPassword);
  return false;
}

String fetchDeviceMode() {
  WiFiClient client;
  HTTPClient http;

  http.setConnectTimeout(cfg.connectTimeoutMs);
  http.setTimeout(cfg.requestTimeoutMs);

  if (!http.begin(client, modeUrl)) {
    Serial.println("Mode poll begin() failed");
    return "";
  }

  http.addHeader("Accept", "application/json");
  int code = http.GET();

  if (code != HTTP_CODE_OK) {
    if (code < 0) {
      Serial.printf("Mode poll HTTP error: %d\n", code);
    } else {
      Serial.printf("Mode poll status: %d\n", code);
    }
    http.end();
    return "";
  }

  String body = http.getString();
  http.end();

  String mode = extractJsonString(body, "mode");
  if (mode != "idle" && mode != "register" && mode != "attendance") {
    return "";
  }

  return mode;
}

bool captureAndSendToBackend() {
  camera_fb_t* fb = esp_camera_fb_get();
  if (fb == nullptr || fb->len == 0) {
    Serial.println("Camera frame capture failed");
    if (fb != nullptr) {
      esp_camera_fb_return(fb);
    }
    return false;
  }

  String responseBody;
  int statusCode = -1;
  bool success = postFrameAsBase64Json(fb, responseBody, statusCode);

  esp_camera_fb_return(fb);

  if (!success) {
    Serial.printf("POST /api/recognize failed. code=%d\n", statusCode);
    return false;
  }

  String status = extractJsonString(responseBody, "status");
  if (status == "present") {
    String name = extractJsonString(responseBody, "name");
    Serial.printf("Present: %s\n", name.c_str());
    beepPattern("entry");
  } else if (status == "unknown") {
    Serial.println("Unknown face");
    beepPattern("unknown");
  } else if (status == "no_face") {
    Serial.println("No face detected");
  } else if (status == "error") {
    Serial.println("Backend returned error status");
    beepPattern("error");
  } else {
    Serial.printf("Status: %s\n", status.c_str());
  }

  return true;
}

bool postFrameAsBase64Json(camera_fb_t* fb, String& responseBody, int& httpCode) {
  responseBody = "";
  httpCode = -1;

  if (fb == nullptr || fb->buf == nullptr || fb->len == 0) {
    return false;
  }

  char* payload = nullptr;
  size_t payloadLen = 0;
  if (!buildRecognizePayload(fb->buf, fb->len, &payload, &payloadLen)) {
    Serial.println("Failed to build JSON payload");
    return false;
  }

  bool requestOk = false;
  for (uint8_t attempt = 0; attempt <= cfg.maxPostRetries; attempt++) {
    if (!ensureWiFiConnected()) {
      delay(150);
      continue;
    }

    WiFiClient client;
    HTTPClient http;
    http.setConnectTimeout(cfg.connectTimeoutMs);
    http.setTimeout(cfg.requestTimeoutMs);

    if (!http.begin(client, recognizeUrl)) {
      Serial.println("Recognize begin() failed");
      delay(120);
      continue;
    }

    http.addHeader("Content-Type", "application/json");
    http.addHeader("Accept", "application/json");

    httpCode = http.POST((uint8_t*)payload, payloadLen);

    if (httpCode > 0) {
      responseBody = http.getString();
      requestOk = (httpCode == HTTP_CODE_OK);
      http.end();
      if (requestOk) {
        break;
      }
    } else {
      Serial.printf("HTTP POST transport error: %d\n", httpCode);
      http.end();
    }

    delay(150);
  }

  free(payload);
  payload = nullptr;

  return requestOk;
}

char* allocBuffer(size_t sizeBytes) {
  if (sizeBytes == 0) {
    return nullptr;
  }

  char* buffer = nullptr;
  if (psramFound()) {
    buffer = (char*)ps_malloc(sizeBytes);
  }
  if (buffer == nullptr) {
    buffer = (char*)malloc(sizeBytes);
  }
  return buffer;
}

bool buildRecognizePayload(const uint8_t* imageData, size_t imageLen, char** outPayload, size_t* outLen) {
  *outPayload = nullptr;
  *outLen = 0;

  if (imageData == nullptr || imageLen == 0) {
    return false;
  }

  const size_t b64Capacity = (4 * ((imageLen + 2) / 3)) + 1;
  char* b64 = allocBuffer(b64Capacity);
  if (b64 == nullptr) {
    return false;
  }

  size_t b64OutLen = 0;
  int encResult = mbedtls_base64_encode(
    (unsigned char*)b64,
    b64Capacity,
    &b64OutLen,
    imageData,
    imageLen
  );

  if (encResult != 0 || b64OutLen == 0) {
    free(b64);
    return false;
  }
  b64[b64OutLen] = '\0';

  const char* prefix = "{\"image_base64\":\"";
  const char* suffix = "\"}";
  const size_t payloadLen = strlen(prefix) + b64OutLen + strlen(suffix);

  char* payload = allocBuffer(payloadLen + 1);
  if (payload == nullptr) {
    free(b64);
    return false;
  }

  memcpy(payload, prefix, strlen(prefix));
  memcpy(payload + strlen(prefix), b64, b64OutLen);
  memcpy(payload + strlen(prefix) + b64OutLen, suffix, strlen(suffix));
  payload[payloadLen] = '\0';

  free(b64);

  *outPayload = payload;
  *outLen = payloadLen;
  return true;
}

void handleBuzzer() {
  if (!server.hasArg("plain")) {
    server.send(400, "application/json", "{\"status\":\"error\",\"message\":\"missing body\"}");
    return;
  }

  String body = server.arg("plain");
  String pattern = extractJsonString(body, "pattern");

  if (pattern == "entry") {
    beepPattern("entry");
  } else if (pattern == "exit") {
    beepPattern("exit");
  } else if (pattern == "unknown") {
    beepPattern("unknown");
  } else if (pattern == "cooldown") {
    beepPattern("cooldown");
  } else {
    beepPattern("error");
  }

  server.send(200, "application/json", "{\"status\":\"ok\"}");
}

void beepPattern(const String& pattern) {
  if (pattern == "entry") {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(120);
    digitalWrite(BUZZER_PIN, LOW);
  } else if (pattern == "exit") {
    for (int i = 0; i < 2; i++) {
      digitalWrite(BUZZER_PIN, HIGH);
      delay(100);
      digitalWrite(BUZZER_PIN, LOW);
      delay(100);
    }
  } else if (pattern == "unknown") {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(350);
    digitalWrite(BUZZER_PIN, LOW);
  } else if (pattern == "cooldown") {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(80);
    digitalWrite(BUZZER_PIN, LOW);
    delay(60);
    digitalWrite(BUZZER_PIN, HIGH);
    delay(80);
    digitalWrite(BUZZER_PIN, LOW);
  } else {
    for (int i = 0; i < 3; i++) {
      digitalWrite(BUZZER_PIN, HIGH);
      delay(70);
      digitalWrite(BUZZER_PIN, LOW);
      delay(70);
    }
  }
}

String extractJsonString(const String& jsonText, const char* key) {
  String token = String("\"") + key + "\"";
  int keyPos = jsonText.indexOf(token);
  if (keyPos < 0) {
    return "";
  }

  int colonPos = jsonText.indexOf(':', keyPos + token.length());
  if (colonPos < 0) {
    return "";
  }

  int startQuote = jsonText.indexOf('"', colonPos + 1);
  if (startQuote < 0) {
    return "";
  }

  int endQuote = jsonText.indexOf('"', startQuote + 1);
  if (endQuote < 0) {
    return "";
  }

  return jsonText.substring(startQuote + 1, endQuote);
}
