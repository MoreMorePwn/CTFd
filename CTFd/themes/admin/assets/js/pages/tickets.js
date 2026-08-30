import "./main";

import $ from "jquery";
import { htmlEntities } from "@ctfdio/ctfd-js/utils/html";

import CTFd from "../compat/CTFd";
import { ezAlert } from "../compat/ezq";

const initialState = window.TICKETS_ADMIN || {};
const state = {
  tickets: initialState.tickets || [],
  targets: initialState.targets || [],
  selectedStatus: initialState.selectedStatus || "all",
  selectedTarget: null,
  resolvingTicketId: null,
};

const statusLabels = {
  pending: "Pending",
  ongoing: "Ongoing",
  resolved: "Resolve",
};

const statusClasses = {
  pending: "badge-warning",
  ongoing: "badge-info",
  resolved: "badge-success",
};

function showError(message) {
  ezAlert({
    title: "Error",
    body: htmlEntities(message || "Ticket update failed."),
    button: "OK",
  });
}

function requestJSON(url, method, body) {
  return CTFd.fetch(url, {
    method: method,
    body: body ? JSON.stringify(body) : undefined,
  }).then((response) => {
    return response.json().then((data) => {
      if (!response.ok || !data.success) {
        const errors = data.errors || {};
        const message = Object.keys(errors)
          .map((key) =>
            errors[key].join ? errors[key].join(" ") : errors[key],
          )
          .join(" ");
        throw new Error(message || "Ticket update failed.");
      }
      return data;
    });
  });
}

function badge(label, className) {
  return `<span class="badge ${className}">${htmlEntities(label)}</span>`;
}

function renderStatus(ticket) {
  const label = statusLabels[ticket.status] || ticket.status;
  const className = statusClasses[ticket.status] || "badge-secondary";
  return badge(label, className);
}

function renderTarget(ticket) {
  const name = htmlEntities(ticket.target_name || "-");
  const type = ticket.target_type === "team" ? "Team" : "User";
  return `
    <div class="font-weight-bold">${name}</div>
    <div class="text-muted small">${type} #${htmlEntities(ticket.target_id || "")}</div>
  `;
}

function renderAction(ticket) {
  if (ticket.status === "pending") {
    return `
      <button type="button" class="btn btn-sm btn-primary ticket-mark-ongoing" data-ticket-id="${ticket.id}">
        Ongoing
      </button>
    `;
  }
  if (ticket.status === "ongoing") {
    return `
      <button type="button" class="btn btn-sm btn-success ticket-open-resolve" data-ticket-id="${ticket.id}">
        Resolve
      </button>
    `;
  }
  return '<span class="text-muted">Final</span>';
}

function filteredTickets() {
  if (state.selectedStatus === "all") {
    return state.tickets;
  }
  return state.tickets.filter(
    (ticket) => ticket.status === state.selectedStatus,
  );
}

function renderTickets() {
  const tickets = filteredTickets();
  const rows = tickets.map((ticket) => {
    const resolveNote = ticket.resolve_note
      ? `<div class="ticket-resolve-preview">${htmlEntities(ticket.resolve_note)}</div>`
      : '<span class="text-muted">Blank</span>';
    return `
      <tr data-ticket-id="${ticket.id}">
        <td class="col-id">${htmlEntities(ticket.id)}</td>
        <td class="col-target">${renderTarget(ticket)}</td>
        <td class="col-message"><div class="ticket-message-preview">${ticket.html || ""}</div></td>
        <td class="col-note">${resolveNote}</td>
        <td class="col-status">${renderStatus(ticket)}</td>
        <td class="col-action">${renderAction(ticket)}</td>
      </tr>
    `;
  });

  $("#tickets-table tbody").html(rows.join(""));
  $("#tickets-empty").toggleClass("d-none", tickets.length > 0);
  updateFilterButtons();
}

function updateFilterButtons() {
  $("[data-ticket-filter]").each(function () {
    const $button = $(this);
    const active = $button.data("ticket-filter") === state.selectedStatus;
    $button.toggleClass("btn-primary", active);
    $button.toggleClass("btn-outline-primary", !active);
  });
}

function renderTargets() {
  const query = ($("#ticket-target-search").val() || "").toLowerCase();
  const targets = state.targets.filter((target) => {
    return (
      (target.name || "").toLowerCase().includes(query) ||
      (target.email || "").toLowerCase().includes(query) ||
      (target.affiliation || "").toLowerCase().includes(query)
    );
  });

  const rows = targets.map((target) => {
    const badges = [];
    if (target.bracket) {
      badges.push(badge(target.bracket, "badge-secondary"));
    }
    if (target.hidden) {
      badges.push(badge("Hidden", "badge-warning"));
    }
    if (target.banned) {
      badges.push(badge("Banned", "badge-danger"));
    }

    return `
      <button type="button" class="list-group-item list-group-item-action ticket-target-option" data-target-id="${target.id}">
        <span>
          <span class="ticket-target-name">${htmlEntities(target.name || "")}</span>
          <span class="ticket-target-meta d-block">
            ${htmlEntities(target.email || "No email")}
            ${target.affiliation ? ` - ${htmlEntities(target.affiliation)}` : ""}
          </span>
        </span>
        <span class="ticket-badges">${badges.join("")}</span>
      </button>
    `;
  });

  $("#ticket-target-list").html(
    rows.join("") || '<div class="ticket-empty">No matching targets.</div>',
  );
}

function replaceTicket(ticket) {
  const index = state.tickets.findIndex((item) => item.id === ticket.id);
  if (index === -1) {
    state.tickets.unshift(ticket);
  } else {
    state.tickets.splice(index, 1, ticket);
  }
  renderTickets();
}

function openTargetModal() {
  $("#ticket-target-search").val("");
  renderTargets();
  $("#ticket-target-modal").modal("show");
}

function openCreateModal(target) {
  state.selectedTarget = target;
  $("#ticket-selected-target").text(target.name || "");
  $("#ticket-title").val("");
  $("#ticket-message").val("");
  $("#ticket-type-toast").prop("checked", true);
  $("#ticket-sound").prop("checked", true);
  $("#ticket-target-modal").modal("hide");
  $("#ticket-create-modal").modal("show");
}

function createTicket(event) {
  event.preventDefault();
  if (!state.selectedTarget) {
    showError("Choose a target first.");
    return;
  }

  const $form = $("#ticket-create-form");
  $form.find("button[type=submit]").prop("disabled", true);

  requestJSON("/api/v1/tickets", "POST", {
    target_id: state.selectedTarget.id,
    title: $("#ticket-title").val(),
    message: $("#ticket-message").val(),
    notification_type: $("input[name=notification_type]:checked").val(),
    sound: $("#ticket-sound").is(":checked"),
  })
    .then((response) => {
      state.selectedStatus = "all";
      replaceTicket(response.data);
      $("#ticket-create-modal").modal("hide");
    })
    .catch((error) => showError(error.message))
    .finally(() => {
      $form.find("button[type=submit]").prop("disabled", false);
    });
}

function markOngoing(ticketId) {
  requestJSON(`/api/v1/tickets/${ticketId}`, "PATCH", {
    status: "ongoing",
  })
    .then((response) => replaceTicket(response.data))
    .catch((error) => showError(error.message));
}

function openResolveModal(ticketId) {
  state.resolvingTicketId = ticketId;
  $("#ticket-resolve-note").val("");
  $("#ticket-resolve-modal").modal("show");
}

function resolveTicket(event) {
  event.preventDefault();
  const note = $("#ticket-resolve-note").val();
  requestJSON(`/api/v1/tickets/${state.resolvingTicketId}`, "PATCH", {
    status: "resolved",
    resolve_note: note,
  })
    .then((response) => {
      replaceTicket(response.data);
      $("#ticket-resolve-modal").modal("hide");
    })
    .catch((error) => showError(error.message));
}

$(() => {
  renderTickets();
  renderTargets();

  $("[data-ticket-filter]").on("click", function () {
    state.selectedStatus = $(this).data("ticket-filter");
    renderTickets();
  });
  $("#ticket-add-button").on("click", openTargetModal);
  $("#ticket-target-search").on("input", renderTargets);
  $("#ticket-create-form").on("submit", createTicket);
  $("#ticket-resolve-form").on("submit", resolveTicket);

  $("#ticket-target-list").on("click", ".ticket-target-option", function () {
    const targetId = Number($(this).data("target-id"));
    const target = state.targets.find((item) => item.id === targetId);
    if (target) {
      openCreateModal(target);
    }
  });

  $("#tickets-table").on("click", ".ticket-mark-ongoing", function () {
    markOngoing($(this).data("ticket-id"));
  });

  $("#tickets-table").on("click", ".ticket-open-resolve", function () {
    openResolveModal($(this).data("ticket-id"));
  });
});
