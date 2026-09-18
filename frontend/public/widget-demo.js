(function () {
  "use strict";

  var currentScript =
    document.currentScript ||
    (function () {
      var scripts = document.getElementsByTagName("script");
      return scripts[scripts.length - 1];
    })();

  var config = {
    apiUrl: (currentScript.getAttribute("data-api-url") || "").replace(/\/$/, ""),
    vertical: currentScript.getAttribute("data-vertical") || "",
    color: currentScript.getAttribute("data-color") || "",
    agentName: currentScript.getAttribute("data-agent-name") || "",
    subtitle: currentScript.getAttribute("data-subtitle") || "Te ayudo a dar el primer paso",
    welcomeMessage: currentScript.getAttribute("data-welcome") || "",
    position: currentScript.getAttribute("data-position") || "right"
  };

  if (!config.apiUrl || !config.vertical) {
    console.error(
      "[AI Lead Machine widget] Faltan data-api-url y/o data-vertical en el <script> de embed."
    );
    return;
  }

  var state = {
    open: false,
    conversationId: null,
    sending: false,
    optionsField: null,
    activeOptionsEl: null,
    ready: false
  };

  var side = config.position === "left" ? "left" : "right";

  fetch(config.apiUrl + "/demo/verticals")
    .then(function (response) { return response.json(); })
    .then(function (verticals) {
      var match = verticals.filter(function (v) { return v.key === config.vertical; })[0];
      if (match) {
        config.color = config.color || match.color;
        config.agentName = config.agentName || match.label;
        config.welcomeMessage = config.welcomeMessage || match.welcome;
      }
    })
    .catch(function () {})
    .finally(function () {
      config.color = config.color || "#111827";
      config.agentName = config.agentName || "Agente IA";
      config.welcomeMessage = config.welcomeMessage || "Hola 👋 ¿En qué puedo ayudarte hoy?";
      init();
      trackPageview();
    });

  function trackPageview() {
    // Cada web donde se embeba este widget cuenta como una visita a su
    // propio "page" (namespaced por rubro), separada de las visitas al
    // demo-site de AI Lead Machine.
    fetch(config.apiUrl + "/analytics/pageview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ page: "widget:" + config.vertical })
    }).catch(function () {});
  }

  function init() {
    var styles =
      "* { box-sizing: border-box; }" +
      ":host { color-scheme: light; }" +
      ":host, .alm-root { font-family: Inter, system-ui, -apple-system, 'Segoe UI', sans-serif; }" +
      ".alm-root { position: fixed; bottom: 20px; " + side + ": 20px; z-index: 999999; }" +
      ".alm-bubble { width: 60px; height: 60px; border-radius: 50%; background: " + config.color + "; " +
      "display: flex; align-items: center; justify-content: center; cursor: pointer; " +
      "box-shadow: 0 10px 25px rgba(0,0,0,0.25); border: none; transition: transform 0.15s ease; }" +
      ".alm-bubble:hover { transform: scale(1.06); }" +
      ".alm-bubble svg { width: 26px; height: 26px; }" +
      ".alm-panel { position: absolute; bottom: 76px; " + side + ": 0; width: 370px; max-width: calc(100vw - 24px); " +
      "height: 560px; max-height: 75vh; background: #ffffff; border-radius: 18px; " +
      "box-shadow: 0 20px 45px rgba(0,0,0,0.2); display: none; flex-direction: column; overflow: hidden; " +
      "border: 1px solid rgba(0,0,0,0.06);}" +
      ".alm-panel.alm-open { display: flex; }" +
      ".alm-header { background: " + config.color + "; color: white; padding: 16px 18px; " +
      "display: flex; align-items: center; justify-content: space-between; }" +
      ".alm-header-info strong { display: block; font-size: 14px; }" +
      ".alm-header-info span { display: block; font-size: 11.5px; opacity: 0.8; margin-top: 2px; }" +
      ".alm-close { background: rgba(255,255,255,0.15); border: none; color: white; width: 26px; height: 26px; " +
      "border-radius: 50%; cursor: pointer; font-size: 15px; line-height: 1; }" +
      ".alm-close:hover { background: rgba(255,255,255,0.28); }" +
      ".alm-messages { flex: 1; overflow-y: auto; padding: 16px; background: #f7f8fa; display: flex; flex-direction: column; gap: 10px; }" +
      ".alm-msg { display: flex; }" +
      ".alm-msg.alm-user { justify-content: flex-end; }" +
      ".alm-card { max-width: 84%; border-radius: 13px; overflow: hidden; }" +
      ".alm-msg.alm-assistant .alm-card { background: white; border: 1px solid #e5e7eb; border-bottom-left-radius: 4px; }" +
      ".alm-msg.alm-user .alm-card { background: " + config.color + "; border-bottom-right-radius: 4px; }" +
      ".alm-bubble-text { padding: 10px 13px; font-size: 13px; line-height: 1.45; white-space: pre-wrap; }" +
      ".alm-msg.alm-assistant .alm-bubble-text { color: #1f2937; }" +
      ".alm-msg.alm-user .alm-bubble-text { color: white; }" +
      ".alm-options-list { display: flex; flex-direction: column; }" +
      ".alm-option-row { border: none; border-top: 1px solid #e5e7eb; background: transparent; color: " + config.color + "; " +
      "padding: 10px 13px; font-size: 12.5px; font-weight: 700; text-align: center; cursor: pointer; font-family: inherit; }" +
      ".alm-option-row:hover { background: rgba(0,0,0,0.035); }" +
      ".alm-option-row:active { background: " + config.color + "; color: white; }" +
      ".alm-typing { font-size: 12px; color: #9ca3af; padding: 0 16px 8px; }" +
      ".alm-input-row { padding: 12px; background: white; border-top: 1px solid #e5e7eb; display: flex; gap: 8px; }" +
      ".alm-input-row input { flex: 1; border: 1px solid #d1d5db; border-radius: 10px; padding: 10px 12px; font-size: 13px; outline: none; font-family: inherit; background: white; color: #1f2937; }" +
      ".alm-input-row input:focus { border-color: " + config.color + "; }" +
      ".alm-send { border: none; border-radius: 10px; background: " + config.color + "; color: white; padding: 0 16px; cursor: pointer; font-size: 13px; }" +
      ".alm-send:disabled { opacity: 0.5; cursor: default; }" +
      ".alm-footer-brand { text-align: center; font-size: 9.5px; color: #c1c5cc; padding: 5px 0 9px; }";

    var host = document.createElement("div");
    host.id = "ai-lead-machine-widget-host";
    document.body.appendChild(host);

    var shadow = host.attachShadow({ mode: "open" });

    var styleTag = document.createElement("style");
    styleTag.textContent = styles;
    shadow.appendChild(styleTag);

    var root = document.createElement("div");
    root.className = "alm-root";
    root.innerHTML =
      '<button class="alm-bubble" type="button" aria-label="Abrir chat">' +
      '<svg viewBox="0 0 24 24" fill="white"><path d="M12 2C6.48 2 2 6.03 2 11c0 2.61 1.28 4.95 3.32 6.6-.13 1.13-.5 2.5-1.32 3.4 1.53 0 3.3-.6 4.5-1.4 1.1.4 2.3.6 3.5.6 5.52 0 10-4.03 10-9S17.52 2 12 2z"/></svg>' +
      "</button>" +
      '<div class="alm-panel">' +
      '<div class="alm-header">' +
      '<div class="alm-header-info"><strong>' + escapeHtml(config.agentName) + "</strong>" +
      "<span>" + escapeHtml(config.subtitle) + "</span></div>" +
      '<button class="alm-close" type="button" aria-label="Cerrar chat">×</button>' +
      "</div>" +
      '<div class="alm-messages"></div>' +
      '<div class="alm-typing" style="display:none;">Escribiendo…</div>' +
      '<div class="alm-input-row">' +
      '<input type="text" placeholder="Escribe un mensaje..." />' +
      '<button class="alm-send" type="button">Enviar</button>' +
      "</div>" +
      '<div class="alm-footer-brand">Powered by AI Lead Machine</div>' +
      "</div>";
    shadow.appendChild(root);

    var bubbleBtn = root.querySelector(".alm-bubble");
    var panel = root.querySelector(".alm-panel");
    var closeBtn = root.querySelector(".alm-close");
    var messagesEl = root.querySelector(".alm-messages");
    var typingEl = root.querySelector(".alm-typing");
    var input = root.querySelector(".alm-input-row input");
    var sendBtn = root.querySelector(".alm-send");

    function escapeHtml(text) {
      var div = document.createElement("div");
      div.textContent = text == null ? "" : String(text);
      return div.innerHTML;
    }

    function toggle(open) {
      state.open = open === undefined ? !state.open : open;
      panel.classList.toggle("alm-open", state.open);
      if (state.open && messagesEl.children.length === 0) {
        addAssistantMessage(config.welcomeMessage, null);
      }
    }

    bubbleBtn.addEventListener("click", function () {
      toggle();
    });
    closeBtn.addEventListener("click", function () {
      toggle(false);
    });

    function scrollToBottom() {
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function addUserMessage(text) {
      var row = document.createElement("div");
      row.className = "alm-msg alm-user";
      row.innerHTML = '<div class="alm-card"><div class="alm-bubble-text"></div></div>';
      row.querySelector(".alm-bubble-text").textContent = text;
      messagesEl.appendChild(row);
      scrollToBottom();
    }

    function addAssistantMessage(text, options) {
      // Una pregunta nueva sustituye a los botones de la anterior: si
      // seguía sin responder, ya no tiene sentido dejarla pulsable.
      if (state.activeOptionsEl && state.activeOptionsEl.parentNode) {
        state.activeOptionsEl.remove();
      }
      state.activeOptionsEl = null;

      var row = document.createElement("div");
      row.className = "alm-msg alm-assistant";

      var card = document.createElement("div");
      card.className = "alm-card";

      var bubble = document.createElement("div");
      bubble.className = "alm-bubble-text";
      bubble.textContent = text || "";
      card.appendChild(bubble);

      if (options && options.length > 0) {
        var optionsList = document.createElement("div");
        optionsList.className = "alm-options-list";

        options.forEach(function (option) {
          var optionBtn = document.createElement("button");
          optionBtn.type = "button";
          optionBtn.className = "alm-option-row";
          optionBtn.textContent = option.label;
          optionBtn.addEventListener("click", function () {
            sendMessage(option);
          });
          optionsList.appendChild(optionBtn);
        });

        card.appendChild(optionsList);
        state.activeOptionsEl = optionsList;
      }

      row.appendChild(card);
      messagesEl.appendChild(row);
      scrollToBottom();
    }

    function sendMessage(option) {
      var text = option ? option.label : input.value.trim();
      if (!text || state.sending) return;

      // Quitar los botones en cuanto se elige uno, para no poder
      // pulsarlos dos veces mientras llega la respuesta.
      if (option && state.activeOptionsEl && state.activeOptionsEl.parentNode) {
        state.activeOptionsEl.remove();
        state.activeOptionsEl = null;
      }

      addUserMessage(text);
      if (!option) input.value = "";
      state.sending = true;
      sendBtn.disabled = true;
      typingEl.style.display = "block";

      var payload = {
        vertical: config.vertical,
        message: text,
        conversation_id: state.conversationId,
        source: "widget"
      };

      if (option) {
        payload.field = state.optionsField;
        payload.value = option.value;
      }

      fetch(config.apiUrl + "/demo/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      })
        .then(function (response) {
          if (!response.ok) throw new Error("request failed");
          return response.json();
        })
        .then(function (data) {
          state.conversationId = data.conversation_id;
          state.optionsField = data.options_field || null;
          addAssistantMessage(data.assistant_message, data.options);
        })
        .catch(function () {
          addAssistantMessage(
            "Lo siento, ha ocurrido un problema al conectar con el agente."
          );
        })
        .finally(function () {
          state.sending = false;
          sendBtn.disabled = false;
          typingEl.style.display = "none";
        });
    }

    sendBtn.addEventListener("click", function () {
      sendMessage();
    });
    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter") sendMessage();
    });
  }
})();
