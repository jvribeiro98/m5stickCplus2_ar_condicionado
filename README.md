# Samsung AC Remote for M5StickC Plus2

Transforme seu **M5StickC Plus2** em um controle remoto para ar-condicionado Samsung usando apenas o emissor IR interno.

> **Status:** Em desenvolvimento 🚧

## Recursos

- ✅ Liga / Desliga
- ✅ Controle de temperatura
- ✅ Modos (Cool, Heat, Dry, Fan, Auto)
- ✅ Velocidade do ventilador
- ✅ Swing
- ✅ Turbo
- ✅ Sleep
- ✅ Interface inspirada no CatHack
- ✅ Salva o último estado

---

# Hardware

- M5StickC Plus2
- Nenhum hardware adicional necessário

---

# Instalação

Instale as bibliotecas:

- M5StickCPlus2
- M5Unified
- M5GFX
- IRremoteESP8266

Abra o projeto na Arduino IDE e grave normalmente.

---

# Compatibilidade

Este projeto utiliza a biblioteca **IRremoteESP8266**, que suporta diversos modelos Samsung.

Nem todos os aparelhos utilizam exatamente o mesmo protocolo.

## Se o seu ar não funcionar

Abra uma Issue contendo:

- Marca
- Modelo do ar-condicionado
- Ano (se souber)
- BTUs
- O que funciona e o que não funciona

Exemplo:

```
Marca: Samsung

Modelo: AR12XXXX

12000 BTUs

Power funciona
Temperatura não muda
Swing não funciona
```

Assim será possível adicionar suporte ao seu modelo.

---

# Como adicionar suporte ao seu ar-condicionado

Caso seu modelo utilize um protocolo diferente, existem algumas opções.

## Opção 1 (Recomendada)

Caso possua o controle original:

Utilize um receptor IR (VS1838B, TSOP38238 ou equivalente) para capturar os comandos do controle.

Depois envie:

- protocolo identificado
- código capturado
- modelo do aparelho

Será adicionado suporte ao projeto.

---

## Opção 2

Caso seu modelo já seja suportado pela IRremoteESP8266, basta informar o modelo do aparelho para que seja criada uma configuração específica.

---

## Opção 3

Caso não possua mais o controle original:

Abra uma Issue informando o modelo do aparelho.

Se existir documentação do protocolo, será implementado suporte.

---

# Roadmap

- [ ] Interface redesenhada
- [ ] Ícones animados
- [ ] Perfis favoritos
- [ ] Mais modelos Samsung
- [ ] OTA
- [ ] Web Flasher
- [ ] Suporte para outras marcas

---

# Contribuindo

Pull Requests são bem-vindos.

Caso possua outro modelo Samsung, testes são muito bem-vindos.

---

# Aviso

Este projeto não possui qualquer vínculo com a Samsung.

Samsung é marca registrada de seus respectivos proprietários.
