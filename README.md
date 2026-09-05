<div align="center">

# ❄️ M5StickC Plus2 — Samsung AC Smart Remote

### Controle Remoto Inteligente e Stateful para Ar-Condicionado Samsung com M5StickC Plus2

[![Hardware](https://img.shields.io/badge/Hardware-M5StickC%20Plus2%20(ESP32)-E7352C?style=for-the-badge&logo=espressif&logoColor=white)](https://m5stack.com/)
[![Framework](https://img.shields.io/badge/Framework-Arduino%20%7C%20ESP32%20Core-00979D?style=for-the-badge&logo=arduino&logoColor=white)](https://github.com/espressif/arduino-esp32)
[![IR Engine](https://img.shields.io/badge/IR%20Library-IRremoteESP8266-FF6F00?style=for-the-badge)](https://github.com/crankyoldgit/IRremoteESP8266)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

<p align="center">
  <b>Transforme seu M5StickC Plus2 em um controle de alta precisão para climatizadores Samsung, com interface tátil, máquina de estados completa e persistência em memória flash NVS.</b>
</p>

</div>

---

## 📖 Visão Geral

Diferente de televisores que operam com códigos IR pontuais e curtos, **aparelhos de ar-condicionado exigem transmissão do estado completo** a cada pulso infravermelho (ligado/desligado, temperatura alvo, velocidade da ventoinha, modo de operação, swing das aletas e modos especiais).

Este firmware foi projetado especificamente para o **M5StickC Plus2**, utilizando o LED transmissor infravermelho interno no **GPIO 19** e a biblioteca `IRremoteESP8266` para gerar os trens de pulso Samsung de 114/168 bits com temporização rigorosa.

---

## 🎮 Interface & Controles Físicos

A interface gráfica foi desenhada para a tela colorida de 1.14" (135x240 px) com alto contraste e navegação intuitiva de dois botões:

```text
 ┌───────────────────────────┐
 │   ❄️ SAMSUNG AC REMOTE     │
 │                           │
 │   POWER        : [ ON ]   │
 │ > TEMP         : [ 23°C ] │
 │   MODE         : [ COOL ] │
 │   FAN SPEED    : [ AUTO ] │
 │   SWING        : [ ON ]   │
 │   QUIET MODE   : [ OFF ]  │
 │                           │
 │   BAT: 94%   RTC: 22:30   │
 └───────────────────────────┘
```

### Mapa de Ações:
- **Botão A (Frontal / M5)**: Navega para o próximo item do menu.
- **Segurar Botão A**: Retorna ao item anterior.
- **Botão B (Lateral)**: Alterna o valor ou executa o comando do item selecionado e transmite o sinal IR imediatamente.

---

## ⚡ Recursos Principais

- 🌡️ **Controle de Temperatura Preciso**: Ajuste de 16°C a 30°C com atualização visual instantânea.
- 🔄 **Modos de Operação Suportados**: `COOL` (Frio), `HEAT` (Quente), `AUTO`, `DRY` (Desumidificar) e `FAN` (Ventilação).
- 💨 **Velocidades de Ventilação**: `AUTO`, `LOW`, `MED`, `HIGH` e `TURBO`.
- 💾 **Persistência de Estado (NVS / Preferences)**: Salva automaticamente suas preferências na memória não-volátil do ESP32 para restaurar o estado após desligar.
- 🔋 **Gestão de Energia & Sleep**: Economia de bateria integrada com desligamento automático do display após inatividade.
- 📡 **Transmissão Direta no GPIO 19**: Sem necessidade de circuitos externos ou soldas adicionais.

---

## 🛠️ Como Compilar e Gravar

### Pré-requisitos
1. **Arduino IDE 2.x** ou **PlatformIO / VS Code**.
2. Pacote de placas **ESP32** instalado na IDE.
3. Bibliotecas requeridas no gerenciador da IDE:
   - `M5StickCPlus2` (versão 1.0.1+)
   - `IRremoteESP8266` (versão 2.8.6+)

### Passo a Passo no Arduino IDE
1. Abra o arquivo [`meu_ar_stick.ino`](meu_ar_stick.ino).
2. Conecte o M5StickC Plus2 via cabo USB-C.
3. Selecione a placa: **`M5StickC Plus2`** (ou `ESP32-PICO-D4 / ESP32 Dev Module`).
4. Defina a porta COM correta.
5. Clique em **Upload** (Gravar).

---

## ⚙️ Adaptação para Outras Marcas

Para utilizar este código com fabricantes diferentes (LG, Daikin, Fujitsu, Gree, Mitsubishi):

1. Localize a classe correspondente na biblioteca `IRremoteESP8266` (ex: `IRLgAc`, `IRDaikinESP`, `IRGreeAC`).
2. Substitua o `#include <ir_Samsung.h>` pelo header da marca desejada.
3. Adapte os métodos `sendNormal()` e `applyStateToAc()` para as constantes do novo protocolo.

---

## 📄 Licença

Código aberto disponibilizado sob licença [MIT](LICENSE).
