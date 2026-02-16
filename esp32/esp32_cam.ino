#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>

// Wi-Fi credentials
const char *ssid = "YOUR_WIFI_SSID";
const char *password = "YOUR_WIFI_PASSWORD";

// Backend URL
const char *backendUrl = "http://192.168.4.2:5000/api/recognize";

// GPIO 12 buzzer
const int buzzerPin = 12;

WebServer server(80);

void setupCamera();
void handleStream();
void handleBuzzer();
void beepPattern(const String &pattern);

void setup() {
  Serial.begin(115200);
  pinMode(buzzerPin, OUTPUT);
  digitalWrite(buzzerPin, LOW);

  setupCamera();

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

  server.on("/stream", HTTP_GET, handleStream);
  server.on("/buzzer", HTTP_POST, handleBuzzer);
  server.begin();
}

void loop() {
  server.handleClient();
}

void setupCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = 5;
  config.pin_d1 = 18;
  config.pin_d2 = 19;
  config.pin_d3 = 21;
  config.pin_d4 = 36;
  config.pin_d5 = 39;
  config.pin_d6 = 34;
  config.pin_d7 = 35;
  config.pin_xclk = 0;
  config.pin_pclk = 22;
  config.pin_vsync = 25;
  config.pin_href = 23;
  config.pin_sccb_sda = 26;
  config.pin_sccb_scl = 27;
  config.pin_pwdn = 32;
  config.pin_reset = -1;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed 0x%x", err);
    beepPattern("error");
    return;
  }
}

void handleStream() {
  WiFiClient client = server.client();
  String boundary = "frame";
  server.sendContent("HTTP/1.1 200 OK\r\n");
  server.sendContent("Content-Type: multipart/x-mixed-replace; boundary=" + boundary + "\r\n\r\n");
  while (client.connected()) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
      break;
    }
    server.sendContent("--" + boundary + "\r\n");
    server.sendContent("Content-Type: image/jpeg\r\n");
    server.sendContent("Content-Length: " + String(fb->len) + "\r\n\r\n");
    client.write(fb->buf, fb->len);
    server.sendContent("\r\n");
    esp_camera_fb_return(fb);
    delay(30);
  }
}

void handleBuzzer() {
  if (!server.hasArg("plain")) {
    server.send(400, "application/json", "{\"error\":\"missing body\"}");
    return;
  }
  String body = server.arg("plain");
  if (body.indexOf("entry") >= 0) {
    beepPattern("entry");
  } else if (body.indexOf("exit") >= 0) {
    beepPattern("exit");
  } else if (body.indexOf("unknown") >= 0) {
    beepPattern("unknown");
  } else {
    beepPattern("error");
  }
  server.send(200, "application/json", "{\"status\":\"ok\"}");
}

void beepPattern(const String &pattern) {
  if (pattern == "entry") {
    digitalWrite(buzzerPin, HIGH);
    delay(120);
    digitalWrite(buzzerPin, LOW);
  } else if (pattern == "exit") {
    for (int i = 0; i < 2; i++) {
      digitalWrite(buzzerPin, HIGH);
      delay(100);
      digitalWrite(buzzerPin, LOW);
      delay(100);
    }
  } else if (pattern == "unknown") {
    digitalWrite(buzzerPin, HIGH);
    delay(400);
    digitalWrite(buzzerPin, LOW);
  } else {
    for (int i = 0; i < 3; i++) {
      digitalWrite(buzzerPin, HIGH);
      delay(80);
      digitalWrite(buzzerPin, LOW);
      delay(80);
    }
  }
}