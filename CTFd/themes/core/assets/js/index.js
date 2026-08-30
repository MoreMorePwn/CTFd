import CTFd from "@ctfdio/ctfd-js";

import dayjs from "dayjs";
import advancedFormat from "dayjs/plugin/advancedFormat";

import times from "./theme/times";
import styles from "./theme/styles";
import highlight from "./theme/highlight";

import alerts from "./utils/alerts";
import tooltips from "./utils/tooltips";
import collapse from "./utils/collapse";

import eventAlerts from "./utils/notifications/alerts";
import eventToasts from "./utils/notifications/toasts";
import eventRead from "./utils/notifications/read";
import ticketPendingAlerts from "./utils/tickets/pending";

import "./components/language";

dayjs.extend(advancedFormat);
CTFd.init(window.init);

function installReliableEventSound() {
  const howl = CTFd.events && CTFd.events.howl;
  if (!howl || howl._ctfdReliablePlayInstalled) {
    return;
  }

  const originalPlay = howl.play.bind(howl);
  const interactionEvents = ["click", "pointerdown", "touchend", "keydown"];
  let queuedRetries = 0;
  let listeningForInteraction = false;

  const isAudioLocked = () => {
    return Boolean(
      window.Howler &&
        window.Howler._audioUnlocked === false &&
        window.Howler.ctx &&
        window.Howler.ctx.state !== "running",
    );
  };

  const playOriginalAfterResume = () => {
    const context = window.Howler && window.Howler.ctx;
    if (context && context.state !== "running" && context.resume) {
      try {
        const resume = context.resume();
        if (resume && typeof resume.then === "function") {
          resume
            .then(() => {
              originalPlay();
            })
            .catch(() => {
              originalPlay();
            });
          return;
        }
      } catch (e) {}
    }

    originalPlay();
  };

  const clearInteractionListeners = () => {
    interactionEvents.forEach(eventName => {
      document.removeEventListener(eventName, flushQueuedRetries, true);
    });
    listeningForInteraction = false;
  };

  const flushQueuedRetries = () => {
    if (!queuedRetries) {
      clearInteractionListeners();
      return;
    }

    const retries = queuedRetries;
    queuedRetries = 0;
    clearInteractionListeners();

    for (let i = 0; i < retries; i++) {
      try {
        playOriginalAfterResume();
      } catch (e) {}
    }
  };

  const queueRetry = () => {
    queuedRetries += 1;
    if (listeningForInteraction) {
      return;
    }

    listeningForInteraction = true;
    interactionEvents.forEach(eventName => {
      document.addEventListener(eventName, flushQueuedRetries, {
        capture: true,
        once: true,
      });
    });

    if (typeof howl.once === "function") {
      howl.once("unlock", flushQueuedRetries);
    }
  };

  howl.play = (...args) => {
    let soundId = null;
    const onPlayError = failedId => {
      if (soundId === null || failedId === soundId) {
        queueRetry();
      }
    };

    if (isAudioLocked()) {
      queueRetry();
      return soundId;
    }

    try {
      if (typeof howl.once === "function") {
        howl.once("playerror", onPlayError);
      }

      soundId = originalPlay(...args);
      if (soundId === null || soundId === undefined) {
        queueRetry();
      }
    } catch (e) {
      queueRetry();
    } finally {
      if (typeof howl.off === "function") {
        setTimeout(() => {
          howl.off("playerror", onPlayError);
        }, 2000);
      }
    }

    return soundId;
  };

  howl._ctfdReliablePlayInstalled = true;
}

installReliableEventSound();

(() => {
  styles();
  times();
  highlight();

  alerts();
  tooltips();
  collapse();

  eventRead();
  eventAlerts();
  eventToasts();
  ticketPendingAlerts();
})();

export default CTFd;
