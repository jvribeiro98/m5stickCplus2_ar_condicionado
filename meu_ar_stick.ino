#include <M5StickCPlus2.h>
#include <IRremoteESP8266.h>
#include <ir_Samsung.h>
#include <Preferences.h>

// ============================================================
// Samsung AC Remote - M5StickC Plus2
// Interface inspirada em controles visuais como o CatHack.
//
// Controles:
//   Botão A       -> próximo item
//   Segurar A     -> item anterior
//   Botão B       -> executar item
//
// A biblioteca M5StickCPlus2 1.0.1 expõe apenas BtnA e BtnB.
// Para ligar/desligar o ar, selecione POWER na interface.
//
// Hardware:
//   Emissor IR interno do M5StickC Plus2: GPIO 19
// ============================================================

constexpr uint16_t IR_PIN = 19;
constexpr uint8_t MENU_COUNT = 8;

IRSamsungAc ac(IR_PIN);
Preferences prefs;

struct AcState {
  bool power = false;
  uint8_t temp = 23;
  uint8_t mode = kSamsungAcCool;
  uint8_t fan = kSamsungAcFanAuto;
  bool swing = true;
  bool turbo = false;
  uint16_t sleepMinutes = 0;
};

AcState state;
uint8_t selected = 0;

String toast;
uint32_t toastUntil = 0;

// Evita gravações repetidas demais na flash.
bool savePending = false;
uint32_t saveAt = 0;

// ------------------------------------------------------------
// Cores
// ------------------------------------------------------------
constexpr uint16_t BG       = 0x0000;
constexpr uint16_t PANEL    = 0x18E3;
constexpr uint16_t BORDER   = 0x4208;
constexpr uint16_t SELECTED = 0x04FF;
constexpr uint16_t TEXT     = 0xFFFF;
constexpr uint16_t MUTED    = 0xAD55;
constexpr uint16_t GREEN_ON = 0x07E0;
constexpr uint16_t RED_OFF  = 0xF800;
constexpr uint16_t YELLOW_UI = 0xFFE0;

// ------------------------------------------------------------
// Nomes
// ------------------------------------------------------------
const char* modeName(uint8_t mode) {
  switch (mode) {
    case kSamsungAcAuto: return "AUTO";
    case kSamsungAcCool: return "FRIO";
    case kSamsungAcDry:  return "SECO";
    case kSamsungAcFan:  return "VENT";
    case kSamsungAcHeat: return "QUENTE";
    default:             return "?";
  }
}

const char* fanName(uint8_t fan) {
  switch (fan) {
    case kSamsungAcFanAuto:
    case kSamsungAcFanAuto2: return "AUTO";
    case kSamsungAcFanLow:   return "BAIXO";
    case kSamsungAcFanMed:   return "MEDIO";
    case kSamsungAcFanHigh:  return "ALTO";
    case kSamsungAcFanTurbo: return "TURBO";
    default:                 return "?";
  }
}

String sleepName() {
  if (state.sleepMinutes == 0) return "OFF";
  return String(state.sleepMinutes / 60) + "H";
}

// ------------------------------------------------------------
// Persistência
// ------------------------------------------------------------
void scheduleSave() {
  savePending = true;
  saveAt = millis() + 800;
}

void saveStateNow() {
  prefs.putBool("power", state.power);
  prefs.putUChar("temp", state.temp);
  prefs.putUChar("mode", state.mode);
  prefs.putUChar("fan", state.fan);
  prefs.putBool("swing", state.swing);
  prefs.putBool("turbo", state.turbo);
  prefs.putUShort("sleep", state.sleepMinutes);
  savePending = false;
}

void loadState() {
  prefs.begin("samsung-ac", false);

  state.power = prefs.getBool("power", false);
  state.temp = prefs.getUChar("temp", 23);
  state.mode = prefs.getUChar("mode", kSamsungAcCool);
  state.fan = prefs.getUChar("fan", kSamsungAcFanAuto);
  state.swing = prefs.getBool("swing", true);
  state.turbo = prefs.getBool("turbo", false);
  state.sleepMinutes = prefs.getUShort("sleep", 0);

  if (state.temp < kSamsungAcMinTemp || state.temp > kSamsungAcMaxTemp) {
    state.temp = 23;
  }

  if (state.mode > kSamsungAcHeat) {
    state.mode = kSamsungAcCool;
  }
}

// ------------------------------------------------------------
// IR
// ------------------------------------------------------------
void applyStateToAc() {
  ac.setPower(state.power);
  ac.setMode(state.mode);
  ac.setTemp(state.temp);
  ac.setFan(state.fan);
  ac.setSwing(state.swing);
  ac.setPowerful(state.turbo);

  // Mantemos extras desligados para maior compatibilidade.
  ac.setQuiet(false);
  ac.setBreeze(false);
  ac.setEcono(false);
  ac.setClean(false);
  ac.setIon(false);
  ac.setBeep(false);
}

void showToast(const String& message, uint16_t duration = 900) {
  toast = message;
  toastUntil = millis() + duration;
}

void sendNormal(const String& message) {
  applyStateToAc();
  ac.send();
  showToast(message);
  scheduleSave();

  Serial.println(ac.toString());
}

void sendExtended(const String& message) {
  applyStateToAc();

  if (state.sleepMinutes > 0) {
    ac.setSleepTimer(state.sleepMinutes);
  } else {
    ac.setSleepTimer(0);
  }

  ac.sendExtended();
  showToast(message);
  scheduleSave();

  Serial.println(ac.toString());
}

void togglePower() {
  state.power = !state.power;
  applyStateToAc();

  if (state.power) {
    ac.sendOn();
    delay(120);

    // Envia também o estado completo desejado.
    applyStateToAc();
    ac.send();

    showToast("LIGANDO");
  } else {
    ac.sendOff();
    showToast("DESLIGANDO");
  }

  scheduleSave();
}

// ------------------------------------------------------------
// Alterações de estado
// ------------------------------------------------------------
void decreaseTemp() {
  if (state.temp > kSamsungAcMinTemp) state.temp--;
  state.power = true;
  sendNormal("TEMP -");
}

void increaseTemp() {
  if (state.temp < kSamsungAcMaxTemp) state.temp++;
  state.power = true;
  sendNormal("TEMP +");
}

void nextMode() {
  switch (state.mode) {
    case kSamsungAcAuto: state.mode = kSamsungAcCool; break;
    case kSamsungAcCool: state.mode = kSamsungAcDry;  break;
    case kSamsungAcDry:  state.mode = kSamsungAcFan;  break;
    case kSamsungAcFan:  state.mode = kSamsungAcHeat; break;
    default:             state.mode = kSamsungAcAuto; break;
  }

  if (state.mode == kSamsungAcAuto) {
    state.temp = kSamsungAcAutoTemp;
    state.fan = kSamsungAcFanAuto2;
  } else if (state.fan == kSamsungAcFanAuto2) {
    state.fan = kSamsungAcFanAuto;
  }

  state.turbo = false;
  state.power = true;
  sendNormal("MODO " + String(modeName(state.mode)));
}

void nextFan() {
  // Em AUTO e SECO alguns aparelhos limitam a ventilação.
  if (state.mode == kSamsungAcAuto || state.mode == kSamsungAcDry) {
    state.fan = (state.mode == kSamsungAcAuto)
                  ? kSamsungAcFanAuto2
                  : kSamsungAcFanAuto;

    showToast("FAN AUTOMATICO");
    return;
  }

  switch (state.fan) {
    case kSamsungAcFanAuto:
    case kSamsungAcFanAuto2: state.fan = kSamsungAcFanLow;  break;
    case kSamsungAcFanLow:   state.fan = kSamsungAcFanMed;  break;
    case kSamsungAcFanMed:   state.fan = kSamsungAcFanHigh; break;
    default:                 state.fan = kSamsungAcFanAuto; break;
  }

  state.turbo = false;
  state.power = true;
  sendNormal("FAN " + String(fanName(state.fan)));
}

void toggleSwing() {
  state.swing = !state.swing;
  state.power = true;
  sendNormal(state.swing ? "SWING ON" : "SWING OFF");
}

void toggleTurbo() {
  state.turbo = !state.turbo;
  state.power = true;

  if (state.turbo) {
    state.fan = kSamsungAcFanTurbo;
  } else {
    state.fan = kSamsungAcFanAuto;
  }

  sendNormal(state.turbo ? "TURBO ON" : "TURBO OFF");
}

void cycleSleep() {
  switch (state.sleepMinutes) {
    case 0:   state.sleepMinutes = 60;  break;
    case 60:  state.sleepMinutes = 120; break;
    case 120: state.sleepMinutes = 240; break;
    default:  state.sleepMinutes = 0;   break;
  }

  state.power = true;
  sendExtended("SLEEP " + sleepName());
}

void executeSelected() {
  switch (selected) {
    case 0: decreaseTemp(); break;
    case 1: increaseTemp(); break;
    case 2: nextMode();     break;
    case 3: nextFan();      break;
    case 4: toggleSwing();  break;
    case 5: toggleTurbo();  break;
    case 6: cycleSleep();   break;
    case 7: togglePower();  break;
  }
}

// ------------------------------------------------------------
// Interface
// ------------------------------------------------------------
void drawHeader() {
  auto& d = StickCP2.Display;

  d.fillRoundRect(4, 3, 232, 52, 7, PANEL);

  d.setTextDatum(top_left);
  d.setTextSize(1);
  d.setTextColor(MUTED, PANEL);
  d.drawString("SAMSUNG DIGITAL INVERTER", 11, 8);

  d.setTextDatum(middle_left);
  d.setTextSize(3);
  d.setTextColor(TEXT, PANEL);
  d.drawString(String(state.temp) + "C", 12, 34);

  d.setTextDatum(middle_center);
  d.setTextSize(1);
  d.setTextColor(YELLOW_UI, PANEL);
  d.drawString(modeName(state.mode), 122, 31);
  d.setTextColor(MUTED, PANEL);
  d.drawString("FAN " + String(fanName(state.fan)), 122, 44);

  d.setTextDatum(middle_right);
  d.setTextColor(state.power ? GREEN_ON : RED_OFF, PANEL);
  d.drawString(state.power ? "ON" : "OFF", 226, 20);

  d.setTextColor(MUTED, PANEL);
  d.drawString(state.swing ? "SWING" : "-", 226, 35);
  d.drawString(state.turbo ? "TURBO" : sleepName(), 226, 47);
}

void drawMenuButton(uint8_t index, int x, int y, int w, int h,
                    const String& label, const String& value = "") {
  auto& d = StickCP2.Display;
  const bool active = index == selected;

  const uint16_t fill = active ? SELECTED : PANEL;
  const uint16_t border = active ? TEXT : BORDER;
  const uint16_t foreground = active ? BG : TEXT;

  d.fillRoundRect(x, y, w, h, 6, fill);
  d.drawRoundRect(x, y, w, h, 6, border);

  d.setTextDatum(middle_center);
  d.setTextSize(1);
  d.setTextColor(foreground, fill);

  if (value.length()) {
    d.drawString(label, x + w / 2, y + 9);
    d.setTextColor(active ? BG : YELLOW_UI, fill);
    d.drawString(value, x + w / 2, y + 23);
  } else {
    d.drawString(label, x + w / 2, y + h / 2);
  }
}

void drawFooter() {
  auto& d = StickCP2.Display;

  d.fillRect(0, 122, 240, 13, BG);
  d.setTextDatum(middle_center);
  d.setTextSize(1);

  if (toast.length() && millis() < toastUntil) {
    d.setTextColor(GREEN_ON, BG);
    d.drawString(toast, 120, 128);
  } else {
    toast = "";
    d.setTextColor(MUTED, BG);
    d.drawString("A NAVEGA   B OK", 120, 128);
  }
}

void drawScreen() {
  auto& d = StickCP2.Display;

  d.startWrite();
  d.fillScreen(BG);

  drawHeader();

  // Grade 4 colunas x 2 linhas.
  constexpr int startX = 4;
  constexpr int startY = 59;
  constexpr int gap = 3;
  constexpr int buttonW = 56;
  constexpr int buttonH = 28;

  drawMenuButton(0, startX + 0 * (buttonW + gap), startY, buttonW, buttonH,
                 "TEMP", "-");
  drawMenuButton(1, startX + 1 * (buttonW + gap), startY, buttonW, buttonH,
                 "TEMP", "+");
  drawMenuButton(2, startX + 2 * (buttonW + gap), startY, buttonW, buttonH,
                 "MODO", modeName(state.mode));
  drawMenuButton(3, startX + 3 * (buttonW + gap), startY, buttonW, buttonH,
                 "FAN", fanName(state.fan));

  drawMenuButton(4, startX + 0 * (buttonW + gap), startY + buttonH + gap,
                 buttonW, buttonH, "SWING", state.swing ? "ON" : "OFF");
  drawMenuButton(5, startX + 1 * (buttonW + gap), startY + buttonH + gap,
                 buttonW, buttonH, "TURBO", state.turbo ? "ON" : "OFF");
  drawMenuButton(6, startX + 2 * (buttonW + gap), startY + buttonH + gap,
                 buttonW, buttonH, "SLEEP", sleepName());
  drawMenuButton(7, startX + 3 * (buttonW + gap), startY + buttonH + gap,
                 buttonW, buttonH, "POWER", state.power ? "OFF" : "ON");

  drawFooter();
  d.endWrite();
}

// ------------------------------------------------------------
// Setup / Loop
// ------------------------------------------------------------
void setup() {
  Serial.begin(115200);

  auto cfg = M5.config();
  StickCP2.begin(cfg);

  StickCP2.Display.setRotation(1);
  StickCP2.Display.setBrightness(90);
  StickCP2.Display.setTextFont(1);
  StickCP2.Display.setTextWrap(false);

  loadState();

  // Inicializa internamente como desligado para as transições de power.
  ac.stateReset(true, false);
  ac.begin();
  applyStateToAc();

  drawScreen();

  Serial.println();
  Serial.println("Samsung AC Remote iniciado.");
  Serial.println("Aponte o topo do Stick para o ar-condicionado.");
}

void loop() {
  StickCP2.update();

  bool redraw = false;

  if (StickCP2.BtnA.wasClicked()) {
    selected = (selected + 1) % MENU_COUNT;
    redraw = true;
  }

  if (StickCP2.BtnA.wasHold()) {
    selected = (selected + MENU_COUNT - 1) % MENU_COUNT;
    redraw = true;
  }

  if (StickCP2.BtnB.wasClicked()) {
    executeSelected();
    redraw = true;
  }

  static bool toastWasVisible = false;
  const bool toastVisible = toast.length() && millis() < toastUntil;

  if (toastWasVisible && !toastVisible) {
    redraw = true;
  }
  toastWasVisible = toastVisible;

  if (savePending && millis() >= saveAt) {
    saveStateNow();
  }

  if (redraw) {
    drawScreen();
  }

  delay(10);
}