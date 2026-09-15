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
    color: currentScript.getAttribute("data-color") || "#111827",
    agentName: currentScript.getAttribute("data-agent-name") || "Agente IA",
    subtitle: currentScript.getAttribute("data-subtitle") || "Te ayudo a encontrar lo que buscas",
    welcomeMessage:
      currentScript.getAttribute("data-welcome") ||
      "Hola 👋 ¿En qué puedo ayudarte hoy?",
    position: currentScript.getAttribute("data-position") || "right"
  };

  if (!config.apiUrl) {
    console.error(
      "[AI Lead Machine widget] Falta el atributo data-api-url en el <script> de embed."
    );
    return;
  }

  var state = {
    open: false,
    conversationId: null,
    lead: {},
    sending: false,
    visitFormFor: null
  };

  var side = config.position === "left" ? "left" : "right";

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
    ".alm-bubble-text { max-width: 80%; padding: 10px 13px; border-radius: 13px; font-size: 13px; line-height: 1.45; " +
    "white-space: pre-wrap; }" +
    ".alm-msg.alm-assistant .alm-bubble-text { background: white; border: 1px solid #e5e7eb; color: #1f2937; border-bottom-left-radius: 4px; }" +
    ".alm-msg.alm-user .alm-bubble-text { background: " + config.color + "; color: white; border-bottom-right-radius: 4px; }" +
    ".alm-typing { font-size: 12px; color: #9ca3af; padding: 0 16px 8px; }" +
    ".alm-properties { display: flex; flex-direction: column; gap: 10px; margin-top: 4px; }" +
    ".alm-property-card { background: white; border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden; }" +
    ".alm-property-card img { width: 100%; height: 110px; object-fit: cover; display: block; }" +
    ".alm-property-body { padding: 10px 12px; }" +
    ".alm-property-body h4 { margin: 0 0 3px; font-size: 12.5px; color: #111827; }" +
    ".alm-property-body p { margin: 0; font-size: 11px; color: #9ca3af; }" +
    ".alm-property-price { font-size: 13px; font-weight: 700; color: " + config.color + "; margin-top: 4px; display: block; }" +
    ".alm-visit-btn { margin-top: 8px; width: 100%; border: 1px solid " + config.color + "; color: " + config.color + "; " +
    "background: white; border-radius: 8px; padding: 7px; font-size: 11.5px; cursor: pointer; }" +
    ".alm-visit-btn:hover { background: rgba(0,0,0,0.03); }" +
    ".alm-visit-form { padding: 10px 12px; border-top: 1px solid #f0f0f0; display: flex; flex-direction: column; gap: 6px; background: #fafafa; }" +
    ".alm-visit-form input { border: 1px solid #d1d5db; border-radius: 7px; padding: 7px 9px; font-size: 11.5px; width: 100%; outline: none; font-family: inherit; background: white; color: #1f2937; }" +
    ".alm-visit-row { display: flex; gap: 6px; }" +
    ".alm-visit-actions { display: flex; justify-content: flex-end; gap: 6px; margin-top: 2px; }" +
    ".alm-visit-actions button { border: none; border-radius: 7px; padding: 7px 10px; font-size: 11px; cursor: pointer; }" +
    ".alm-visit-cancel { background: #e5e7eb; color: #374151; }" +
    ".alm-visit-confirm { background: " + config.color + "; color: white; }" +
    ".alm-visit-status { font-size: 11px; color: #16a34a; margin-top: 6px; }" +
    ".alm-slots { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }" +
    ".alm-slot-btn { border: 1px solid " + config.color + "; background: white; color: " + config.color + "; " +
    "border-radius: 20px; padding: 5px 10px; font-size: 11px; cursor: pointer; }" +
    ".alm-slot-btn:hover { background: rgba(0,0,0,0.04); }" +
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
      addAssistantMessage(config.welcomeMessage);
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
    row.innerHTML = '<div class="alm-bubble-text"></div>';
    row.querySelector(".alm-bubble-text").textContent = text;
    messagesEl.appendChild(row);
    scrollToBottom();
  }

  function addAssistantMessage(text, properties) {
    var row = document.createElement("div");
    row.className = "alm-msg alm-assistant";

    var bubble = document.createElement("div");
    bubble.className = "alm-bubble-text";
    bubble.textContent = text || "";
    row.appendChild(bubble);

    messagesEl.appendChild(row);

    if (properties && properties.length > 0) {
      var list = document.createElement("div");
      list.className = "alm-properties";

      properties.forEach(function (property) {
        list.appendChild(renderPropertyCard(property));
      });

      messagesEl.appendChild(list);
    }

    scrollToBottom();
  }

  function renderPropertyCard(property) {
    var card = document.createElement("div");
    card.className = "alm-property-card";

    var imageHtml = "";
    if (property.images && property.images.length > 0) {
      imageHtml = '<img src="' + config.apiUrl + property.images[0] + '" alt="" />';
    }

    var priceLabel =
      property.operation === "venta"
        ? formatPrice(property.price) + " €"
        : formatPrice(property.price) + " €/mes";

    card.innerHTML =
      imageHtml +
      '<div class="alm-property-body">' +
      "<h4>" + escapeHtml(property.title) + "</h4>" +
      "<p>" + escapeHtml(property.city) + "</p>" +
      '<span class="alm-property-price">' + priceLabel + "</span>" +
      '<button type="button" class="alm-visit-btn">📅 Agendar visita</button>' +
      "</div>";

    var visitBtn = card.querySelector(".alm-visit-btn");
    visitBtn.addEventListener("click", function () {
      openVisitForm(card, property);
    });

    return card;
  }

  function formatPrice(price) {
    if (price === null || price === undefined) return "";
    return Number(price).toLocaleString("es-ES");
  }

  function openVisitForm(card, property) {
    var existing = card.querySelector(".alm-visit-form");
    if (existing) {
      existing.remove();
      return;
    }

    var form = document.createElement("div");
    form.className = "alm-visit-form";
    form.innerHTML =
      '<div class="alm-visit-row">' +
      '<input type="date" class="alm-visit-date" />' +
      '<input type="time" class="alm-visit-time" />' +
      "</div>" +
      '<input type="text" class="alm-visit-name" placeholder="Nombre" value="' +
      escapeHtml(state.lead.name || "") + '" />' +
      '<input type="tel" class="alm-visit-phone" placeholder="Teléfono" value="' +
      escapeHtml(state.lead.phone || "") + '" />' +
      '<input type="email" class="alm-visit-email" placeholder="Email" value="' +
      escapeHtml(state.lead.email || "") + '" />' +
      '<div class="alm-visit-actions">' +
      '<button type="button" class="alm-visit-cancel">Cancelar</button>' +
      '<button type="button" class="alm-visit-confirm">Confirmar</button>' +
      "</div>";

    card.appendChild(form);

    form.querySelector(".alm-visit-cancel").addEventListener("click", function () {
      form.remove();
    });

    form.querySelector(".alm-visit-confirm").addEventListener("click", function () {
      submitVisit(property.id, form);
    });

    scrollToBottom();
  }

  function submitVisit(propertyId, form, overrideDateTime) {
    var date = form.querySelector(".alm-visit-date").value;
    var time = form.querySelector(".alm-visit-time").value;
    var scheduledAt = overrideDateTime;

    if (!scheduledAt) {
      if (!date || !time) {
        showVisitStatus(form, "Indica fecha y hora para la visita.");
        return;
      }
      scheduledAt = date + "T" + time + ":00";
    }

    var payload = {
      property_id: propertyId,
      scheduled_at: scheduledAt,
      conversation_id: state.conversationId,
      lead_name: form.querySelector(".alm-visit-name").value || null,
      lead_phone: form.querySelector(".alm-visit-phone").value || null,
      lead_email: form.querySelector(".alm-visit-email").value || null
    };

    fetch(config.apiUrl + "/visits", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
      .then(function (response) {
        if (!response.ok) throw new Error("request failed");
        return response.json();
      })
      .then(function (data) {
        showVisitStatus(form, data.message);

        var oldSlots = form.querySelector(".alm-slots");
        if (oldSlots) oldSlots.remove();

        if (data.calendar_status === "unavailable" && data.alternative_slots && data.alternative_slots.length > 0) {
          var slotsWrap = document.createElement("div");
          slotsWrap.className = "alm-slots";

          data.alternative_slots.forEach(function (slot) {
            var slotBtn = document.createElement("button");
            slotBtn.type = "button";
            slotBtn.className = "alm-slot-btn";
            slotBtn.textContent = formatSlotLabel(slot);
            slotBtn.addEventListener("click", function () {
              submitVisit(propertyId, form, slot);
            });
            slotsWrap.appendChild(slotBtn);
          });

          form.appendChild(slotsWrap);
        } else if (data.visit_id) {
          form
            .querySelectorAll("input, .alm-visit-actions")
            .forEach(function (el) {
              el.style.display = "none";
            });
        }

        scrollToBottom();
      })
      .catch(function () {
        showVisitStatus(form, "No se pudo agendar la visita. Inténtalo de nuevo.");
      });
  }

  function showVisitStatus(form, message) {
    var status = form.querySelector(".alm-visit-status");
    if (!status) {
      status = document.createElement("div");
      status.className = "alm-visit-status";
      form.appendChild(status);
    }
    status.textContent = message;
  }

  function formatSlotLabel(isoString) {
    var date = new Date(isoString);
    if (isNaN(date.getTime())) return isoString;
    var days = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];
    var day = days[date.getDay()];
    var d = String(date.getDate()).padStart(2, "0");
    var m = String(date.getMonth() + 1).padStart(2, "0");
    var h = String(date.getHours()).padStart(2, "0");
    var min = String(date.getMinutes()).padStart(2, "0");
    return day + " " + d + "/" + m + " " + h + ":" + min;
  }

  function sendMessage() {
    var text = input.value.trim();
    if (!text || state.sending) return;

    addUserMessage(text);
    input.value = "";
    state.sending = true;
    sendBtn.disabled = true;
    typingEl.style.display = "block";

    fetch(config.apiUrl + "/conversations/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        conversation_id: state.conversationId
      })
    })
      .then(function (response) {
        if (!response.ok) throw new Error("request failed");
        return response.json();
      })
      .then(function (data) {
        state.conversationId = data.conversation_id;
        state.lead = data.lead || {};

        var properties =
          data.result && data.result.status === "matches_found"
            ? data.result.properties
            : null;

        addAssistantMessage(data.assistant_message, properties);
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

  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", function (event) {
    if (event.key === "Enter") sendMessage();
  });
})();
