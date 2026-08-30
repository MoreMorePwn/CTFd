import Alpine from "alpinejs";
import { Modal, Toast } from "bootstrap";

import CTFd from "../../index";

function playTicketSound(ticket) {
  if (!ticket.sound || !CTFd.events || !CTFd.events.howl) {
    return;
  }

  CTFd.events.howl.play();
}

function showTicket(ticket, done) {
  playTicketSound(ticket);

  const data = {
    title: ticket.title || "Ticket",
    html: ticket.html || ticket.content || "",
  };

  if (ticket.type === "alert") {
    Alpine.store("modal", data);
    const modalElement = document.querySelector("[x-ref='modal']");
    if (!modalElement) {
      done();
      return;
    }

    const modal = Modal.getOrCreateInstance(modalElement);
    modalElement.addEventListener("hidden.bs.modal", done, { once: true });
    modal.show();
    return;
  }

  Alpine.store("toast", data);
  const toastElement = document.querySelector("[x-ref='toast']");
  if (!toastElement) {
    done();
    return;
  }

  const toast = Toast.getOrCreateInstance(toastElement);
  toastElement.addEventListener("hidden.bs.toast", done, { once: true });
  toast.show();
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
