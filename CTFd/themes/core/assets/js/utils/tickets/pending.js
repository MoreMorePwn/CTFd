import { Modal, Toast } from "bootstrap";

import CTFd from "../../index";

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
      showTicketQueue(response.data, 0);
    })
    .catch(() => {});
}

export default () => {
  if (!CTFd.user || !CTFd.user.id) {
    return;
  }

  document.addEventListener(
    "alpine:initialized",
    () => {
      loadPendingTickets();
    },
    { once: true },
  );
};
