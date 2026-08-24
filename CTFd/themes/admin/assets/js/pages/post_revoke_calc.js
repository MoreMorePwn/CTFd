import "./main";
import CTFd from "../compat/CTFd";
import $ from "jquery";
import { htmlEntities } from "@ctfdio/ctfd-js/utils/html";
import { ezAlert } from "../compat/ezq";

const settings = window.POST_REVOKE_CALC || {};
let activeAccountId = null;
const noteTimers = {};

function queryString() {
  const params = new URLSearchParams();
  if (settings.bracketId) {
    params.set("bracket_id", settings.bracketId);
  }
  if (settings.sort) {
    params.set("sort", settings.sort);
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

function endpoint(path) {
  return `/api/v1/post-revoke-calc${path}${queryString()}`;
}

function setStatus(message, isError) {
  const status = $("#post-revoke-status");
  status
    .text(message || "")
    .toggleClass("text-danger", Boolean(isError))
    .toggleClass("text-muted", !isError);
}

function errorMessage(response) {
  if (!response || !response.errors) {
    return "Post-Revoke Calc update failed.";
  }
  const parts = [];
  Object.keys(response.errors).forEach((key) => {
    const value = response.errors[key];
    if (Array.isArray(value)) {
      parts.push(value.join("\n"));
    } else {
      parts.push(String(value));
    }
  });
  return parts.join("\n") || "Post-Revoke Calc update failed.";
}

function requestJSON(url, options) {
  return CTFd.fetch(url, {
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    ...options,
  }).then((response) => response.json());
}

function patchJSON(url, payload) {
  setStatus("Saving...");
  return requestJSON(url, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }).then((response) => {
    if (!response.success) {
      throw response;
    }
    setStatus("Saved.");
    return response.data;
  });
}

function updateSummaryRows(rows) {
  rows.forEach((row) => {
    const tr = $(`[data-account-row="${row.account_id}"]`);
    if (!tr.length) {
      return;
    }

    tr.find("[data-rank]").text(row.rank);
    tr.find("[data-pre-score]").text(row.pre_score_display);
    tr.find("[data-post-score]").text(row.post_score_display);
    tr
      .find("[data-score-diff]")
      .text(row.score_delta_display)
      .removeClass("score-diff-positive score-diff-negative score-diff-zero")
      .addClass(`score-diff-${row.score_delta_class || "zero"}`);

    const banInput = tr.find(".post-revoke-account-ban");
    banInput.prop("checked", row.calc_banned);
    banInput.prop("disabled", !settings.canWrite || row.real_banned);

    const noteInput = tr.find(".post-revoke-account-note");
    if (!noteInput.is(":focus")) {
      noteInput.val(row.note || "");
    }
  });
}

function updateChallengeRows(rows) {
  rows.forEach((row) => {
    const tr = $(`[data-challenge-row="${row.challenge_id}"]`);
    if (!tr.length) {
      return;
    }

    tr.find("[data-challenge-pre-score]").text(row.pre_score_display);
    tr.find("[data-challenge-post-score]").text(row.post_score_display);
    tr
      .find("[data-challenge-score-diff]")
      .text(row.score_delta_display)
      .removeClass("score-diff-positive score-diff-negative score-diff-zero")
      .addClass(`score-diff-${row.score_delta_class || "zero"}`);
    tr.find("[data-challenge-solve-count]").text(row.solve_count_display);
  });
}

function scoreText(value) {
  if (value === null || value === undefined || value === "") {
    return "0";
  }
  const number = Number(value);
  if (Number.isInteger(number)) {
    return String(number);
  }
  return number.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
}

function percentText(value) {
  const number = Number(value || 0);
  if (Number.isInteger(number)) {
    return String(number);
  }
  return number.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
}

function renderDetailRows(kind, rows) {
  const title = kind === "solves" ? "Solves" : "Awards";
  const nameHeader = kind === "solves" ? "Challenge" : "Award";
  const emptyText = kind === "solves" ? "No solves" : "No awards";

  let body = "";
  if (!rows.length) {
    body = `<tr><td colspan="6" class="text-muted text-center">${emptyText}</td></tr>`;
  } else {
    body = rows
      .map((item) => {
        const itemName = kind === "solves" ? item.challenge_name : item.name;
        const revoked = item.revoked ? "checked" : "";
        const disabled = settings.canWrite ? "" : "disabled";
        return `
          <tr>
            <td class="col-name">${htmlEntities(itemName || "")}</td>
            <td class="text-right col-score">${scoreText(item.original_score)}</td>
            <td class="text-right col-score">${scoreText(item.post_score)}</td>
            <td class="col-percent">
              <input type="number" min="0" max="100" step="0.01" class="form-control form-control-sm post-revoke-percent" data-kind="${kind}" data-item-id="${item.id}" value="${percentText(item.percentage)}" ${disabled}>
            </td>
            <td class="text-center col-revoke">
              <input type="checkbox" class="post-revoke-item-revoke" data-kind="${kind}" data-item-id="${item.id}" ${revoked} ${disabled}>
            </td>
            <td class="col-note">
              <textarea class="form-control form-control-sm post-revoke-note post-revoke-item-note" rows="1" data-kind="${kind}" data-item-id="${item.id}" ${disabled}>${htmlEntities(item.note || "")}</textarea>
            </td>
          </tr>
        `;
      })
      .join("");
  }

  return `
    <h4 class="mt-3">${title}</h4>
    <div class="table-responsive-lg">
      <table class="table table-sm table-striped border post-revoke-detail-table">
        <thead>
          <tr>
            <th class="col-name">${nameHeader}</th>
            <th class="text-right col-score">Original</th>
            <th class="text-right col-score">After</th>
            <th class="col-percent">Score %</th>
            <th class="text-center col-revoke">Revoke</th>
            <th class="col-note">Note</th>
          </tr>
        </thead>
        <tbody>${body}</tbody>
      </table>
    </div>
  `;
}

function renderAccountMetadata(account) {
  const metadata = account.metadata || {};
  const items = [
    ["Email", metadata.email],
    ["Affiliation", metadata.affiliation],
    ["Country", metadata.country],
  ].filter((item) => item[1]);

  if (!items.length) {
    return "";
  }

  return `
    <div class="post-revoke-account-meta mt-2">
      ${items
        .map(
          ([label, value]) => `
            <div class="post-revoke-account-meta-item">
              <span class="text-muted">${htmlEntities(label)}</span>
              <strong>${htmlEntities(value)}</strong>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderDetail(detail) {
  const account = detail.account;
  activeAccountId = account.account_id;
  $("#post-revoke-detail-panel").html(`
    <div class="d-flex flex-wrap justify-content-between align-items-start">
      <div>
        <h3 class="mb-1">${htmlEntities(account.name)}</h3>
        <div class="text-muted">
          Rank ${account.rank} | Pre ${account.pre_score_display} | Post ${account.post_score_display} | Diff ${account.score_delta_display} | ${account.bracket || "No bracket"}
        </div>
        ${renderAccountMetadata(account)}
      </div>
      <div>
        ${account.calc_banned ? '<span class="badge badge-danger">Banned</span>' : '<span class="badge badge-success">Included</span>'}
      </div>
    </div>
    ${renderDetailRows("solves", detail.solves)}
    ${renderDetailRows("awards", detail.awards)}
  `);
}

function loadDetail(accountId) {
  activeAccountId = accountId;
  setStatus("Loading detail...");
  return requestJSON(endpoint(`/accounts/${accountId}`), {
    method: "GET",
  })
    .then((response) => {
      if (!response.success) {
        throw response;
      }
      renderDetail(response.data);
      setStatus("");
    })
    .catch((response) => {
      setStatus(errorMessage(response), true);
      ezAlert({
        title: "Error!",
        body: errorMessage(response),
        button: "Okay",
      });
    });
}

function refreshAfter(data) {
  updateSummaryRows(data.rows || []);
  updateChallengeRows(data.challenge_rows || []);
  if (activeAccountId) {
    loadDetail(activeAccountId);
  }
}

function saveAccount(accountId, payload) {
  return patchJSON(endpoint(`/accounts/${accountId}`), payload)
    .then(refreshAfter)
    .catch((response) => {
      setStatus(errorMessage(response), true);
      ezAlert({
        title: "Error!",
        body: errorMessage(response),
        button: "Okay",
      });
    });
}

function saveItem(kind, itemId, payload) {
  return patchJSON(endpoint(`/${kind}/${itemId}`), payload)
    .then(refreshAfter)
    .catch((response) => {
      setStatus(errorMessage(response), true);
      ezAlert({
        title: "Error!",
        body: errorMessage(response),
        button: "Okay",
      });
    });
}

function debounceNote(key, callback) {
  if (noteTimers[key]) {
    clearTimeout(noteTimers[key]);
  }
  noteTimers[key] = setTimeout(callback, 600);
}

function setActiveView(view) {
  const isChallengeView = view === "challenges";
  $("#post-revoke-scoreboard-view").toggleClass("d-none", isChallengeView);
  $("#post-revoke-challenge-view").toggleClass("d-none", !isChallengeView);
  $("[data-post-revoke-view-button]").each(function () {
    const target = $(this);
    const active = target.data("post-revoke-view-button") === view;
    target
      .toggleClass("active btn-primary", active)
      .toggleClass("btn-outline-primary", !active)
      .attr("aria-pressed", active ? "true" : "false");
  });
}

$(() => {
  $("[data-post-revoke-view-button]").on("click", function () {
    setActiveView($(this).data("post-revoke-view-button"));
  });

  $("#post-revoke-summary-body").on("click", ".post-revoke-detail-button", function () {
    loadDetail($(this).data("account-id"));
  });

  $("#post-revoke-summary-body").on("change", ".post-revoke-account-ban", function () {
    const target = $(this);
    saveAccount(target.data("account-id"), {
      manual_banned: target.prop("checked"),
    });
  });

  $("#post-revoke-summary-body").on("input", ".post-revoke-account-note", function () {
    const target = $(this);
    const accountId = target.data("account-id");
    debounceNote(`account-${accountId}`, function () {
      saveAccount(accountId, {
        note: target.val(),
      });
    });
  });

  $("#post-revoke-detail-panel").on("change", ".post-revoke-percent", function () {
    const target = $(this);
    saveItem(target.data("kind"), target.data("item-id"), {
      percentage: target.val(),
    });
  });

  $("#post-revoke-detail-panel").on("change", ".post-revoke-item-revoke", function () {
    const target = $(this);
    saveItem(target.data("kind"), target.data("item-id"), {
      revoked: target.prop("checked"),
    });
  });

  $("#post-revoke-detail-panel").on("input", ".post-revoke-item-note", function () {
    const target = $(this);
    const key = `${target.data("kind")}-${target.data("item-id")}`;
    debounceNote(key, function () {
      saveItem(target.data("kind"), target.data("item-id"), {
        note: target.val(),
      });
    });
  });
});
