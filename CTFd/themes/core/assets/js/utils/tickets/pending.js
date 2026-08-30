import { Modal, Toast } from "bootstrap";

import CTFd from "../../index";

const displayedTicketIds = new Set();

function playTicketSound(ticket) {
  if (!ticket.sound || !CTFd.events || !CTFd.events.howl) {
    return;
  }

  try {
    CTFd.events.howl.play();
  } catch (e) {}
}

function ticketTitle(ticket) {
  return ticket.title || "Ticket";
}

function ticketHtml(ticket) {
  return ticket.html || ticket.content || "";
}

function createToastElement(ticket) {
  const wrapper = document.createElement("div");
  wrapper.className = "toast hide";
  wrapper.setAttribute("role", "alert");
  wrapper.setAttribute("aria-live", "assertive");
  wrapper.setAttribute("aria-atomic", "true");
  wrapper.setAttribute("data-bs-autohide", "false");
  wrapper.innerHTML = `
    <div class="toast-header">
      <strong class="me-auto"></strong>
      <small>just now</small>
      <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
    <div class="toast-body"></div>
  `;
  wrapper.querySelector("strong").textContent = ticketTitle(ticket);
  wrapper.querySelector(".toast-body").innerHTML = ticketHtml(ticket);
  return wrapper;
}

function createToastContainer() {
  let container = document.querySelector("[data-ticket-toast-container]");
  if (container) {
    return container;
  }

  container = document.createElement("div");
  container.className = "position-fixed bottom-0 end-0 p-3";
  container.style.zIndex = "12";
  container.setAttribute("data-ticket-toast-container", "true");
  document.body.appendChild(container);
  return container;
}

function createModalElement(ticket) {
  const wrapper = document.createElement("div");
  wrapper.className = "modal fade";
  wrapper.tabIndex = -1;
  wrapper.setAttribute("aria-hidden", "true");
  wrapper.innerHTML = `
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title"></h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <p></p>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-primary" data-bs-dismiss="modal">Got it!</button>
        </div>
      </div>
    </div>
  `;
  wrapper.querySelector(".modal-title").textContent = ticketTitle(ticket);
  wrapper.querySelector(".modal-body p").innerHTML = ticketHtml(ticket);
  return wrapper;
}

function markTicketDisplayed(ticket) {
  if (!ticket || ticket.id === null || ticket.id === undefined) {
    return true;
  }

  const key = String(ticket.id);
  if (displayedTicketIds.has(key)) {
    return false;
  }

  displayedTicketIds.add(key);
  return true;
}

function showTicket(ticket, done) {
  if (ticket.type === "alert") {
    const modalElement = createModalElement(ticket);
    document.body.appendChild(modalElement);
    const modal = Modal.getOrCreateInstance(modalElement);
    modalElement.addEventListener(
      "hidden.bs.modal",
      () => {
        modal.dispose();
        modalElement.remove();
        done();
      },
      { once: true },
    );
    modal.show();
    playTicketSound(ticket);
    return;
  }

  const toastElement = createToastElement(ticket);
  createToastContainer().appendChild(toastElement);
  const toast = Toast.getOrCreateInstance(toastElement);
  toastElement.addEventListener(
    "hidden.bs.toast",
    () => {
      toast.dispose();
      toastElement.remove();
    },
    { once: true },
  );
  toast.show();
  playTicketSound(ticket);
  done();
}

function showTicketQueue(tickets, index) {
  if (index >= tickets.length) {
    return;
  }

  showTicket(tickets[index], () => showTicketQueue(tickets, index + 1));
}

function showTickets(tickets) {
  const unseenTickets = tickets.filter(markTicketDisplayed);
  if (!unseenTickets.length) {
    return;
  }

  showTicketQueue(unseenTickets, 0);
}

function isTicketForCurrentUser(ticket) {
  if (!ticket || !ticket.target_id || !ticket.target_type) {
    return false;
  }

  if (ticket.target_type === "team") {
    return Number(ticket.target_id) === Number(CTFd.team && CTFd.team.id);
  }

  if (ticket.target_type === "user") {
    return Number(ticket.target_id) === Number(CTFd.user && CTFd.user.id);
  }

  return false;
}

function handleRealtimeTicket(ticket) {
  if (!isTicketForCurrentUser(ticket)) {
    return;
  }

  showTickets([ticket]);
}

function connectRealtimeTickets() {
  if (!CTFd.events || !CTFd.events.source || !CTFd.events.controller) {
    return;
  }

  CTFd.events.source.addEventListener(
    "ticket",
    event => {
      let ticket = null;
      try {
        ticket = JSON.parse(event.data);
      } catch (e) {
        return;
      }

      if (!isTicketForCurrentUser(ticket)) {
        return;
      }

      CTFd.events.controller.broadcast("ticket", { ticket });
      showTickets([ticket]);
    },
    false,
  );

  CTFd.events.controller.ticket = data => {
    handleRealtimeTicket(data && data.ticket);
  };
}

function loadPendingTickets() {
  CTFd.fetch("/api/v1/tickets/pending")
    .then(response => {
      if (!response.ok) {
        return null;
      }
      return response.json();
    })
    .then(response => {
      if (!response || !response.success || !response.data.length) {
        return;
      }
      showTickets(response.data);
    })
    .catch(() => {});
}

export default () => {
  if (!CTFd.user || !CTFd.user.id) {
    return;
  }

  connectRealtimeTickets();

  document.addEventListener(
    "alpine:initialized",
    () => {
      loadPendingTickets();
    },
    { once: true },
  );
};
