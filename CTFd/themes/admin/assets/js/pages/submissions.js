import "./main";
import CTFd from "../compat/CTFd";
import $ from "jquery";
import hljs from "highlight.js";
import { htmlEntities } from "@ctfdio/ctfd-js/utils/html";
import { ezQuery } from "../compat/ezq";
import "../compat/format";

const SOLVER_LANGUAGES = {
  bash: "bash",
  bat: "dos",
  c: "c",
  cc: "cpp",
  cpp: "cpp",
  cs: "csharp",
  css: "css",
  go: "go",
  h: "c",
  hpp: "cpp",
  html: "xml",
  java: "java",
  js: "javascript",
  json: "json",
  kt: "kotlin",
  lua: "lua",
  md: "markdown",
  php: "php",
  pl: "perl",
  ps1: "powershell",
  py: "python",
  rb: "ruby",
  rs: "rust",
  sh: "bash",
  sql: "sql",
  ts: "typescript",
  txt: "plaintext",
  xml: "xml",
  yaml: "yaml",
  yml: "yaml",
};

const SOLVER_LANGUAGE_LABELS = {
  bash: "Bash",
  c: "C",
  cpp: "C++",
  csharp: "C#",
  css: "CSS",
  dos: "Batch",
  go: "Go",
  java: "Java",
  javascript: "JavaScript",
  json: "JSON",
  kotlin: "Kotlin",
  lua: "Lua",
  markdown: "Markdown",
  perl: "Perl",
  php: "PHP",
  plaintext: "Plain text",
  powershell: "PowerShell",
  python: "Python",
  ruby: "Ruby",
  rust: "Rust",
  sql: "SQL",
  typescript: "TypeScript",
  xml: "HTML/XML",
  yaml: "YAML",
};

function getSolverLanguage(filename) {
  const cleanName = (filename || "").split("?")[0].split("#")[0];
  const parts = cleanName.split(".");

  if (parts.length < 2) {
    return null;
  }

  return SOLVER_LANGUAGES[parts.pop().toLowerCase()] || null;
}

function getSolverLanguageLabel(language) {
  return SOLVER_LANGUAGE_LABELS[language] || "Plain text";
}

function deleteCorrectSubmission(_event) {
  const key_id = $(this).data("submission-id");
  const $elem = $(this).parent().parent();
  const chal_name = $elem.find(".chal").text().trim();
  const team_name = $elem.find(".team").text().trim();

  const row = $(this).parent().parent();

  ezQuery({
    title: "Delete Submission",
    body: "Are you sure you want to delete correct submission from {0} for challenge {1}".format(
      "<strong>" + htmlEntities(team_name) + "</strong>",
      "<strong>" + htmlEntities(chal_name) + "</strong>",
    ),
    success: function () {
      CTFd.api
        .delete_submission({ submissionId: key_id })
        .then(function (response) {
          if (response.success) {
            row.remove();
          }
        });
    },
  });
}

function deleteSelectedSubmissions(_event) {
  let submissionIDs = $("input[data-submission-id]:checked").map(function () {
    return $(this).data("submission-id");
  });
  let target = submissionIDs.length === 1 ? "submission" : "submissions";

  ezQuery({
    title: "Delete Submissions",
    body: `Are you sure you want to delete ${submissionIDs.length} ${target}?`,
    success: function () {
      const reqs = [];
      for (var subId of submissionIDs) {
        reqs.push(CTFd.api.delete_submission({ submissionId: subId }));
      }
      Promise.all(reqs).then((_responses) => {
        window.location.reload();
      });
    },
  });
}

function correctSubmissions(_event) {
  let submissionIDs = $("input[data-submission-id]:checked").map(function () {
    return $(this).data("submission-id");
  });
  let target = submissionIDs.length === 1 ? "submission" : "submissions";

  ezQuery({
    title: "Correct Submissions",
    body: `Are you sure you want to mark ${submissionIDs.length} ${target} correct?`,
    success: function () {
      const reqs = [];
      for (var subId of submissionIDs) {
        let req = CTFd.fetch(`/api/v1/submissions/${subId}`, {
          method: "PATCH",
          credentials: "same-origin",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ type: "correct" }),
        });
        reqs.push(req);
      }
      Promise.all(reqs).then((_responses) => {
        window.location.reload();
      });
    },
  });
}

function incorrectSubmissions(_event) {
  let submissionIDs = $("input[data-submission-id]:checked").map(function () {
    return $(this).data("submission-id");
  });
  let target = submissionIDs.length === 1 ? "submission" : "submissions";

  ezQuery({
    title: "Incorrect Submissions",
    body: `Are you sure you want to mark ${submissionIDs.length} ${target} incorrect?`,
    success: function () {
      const reqs = [];
      for (var subId of submissionIDs) {
        let req = CTFd.fetch(`/api/v1/submissions/${subId}`, {
          method: "PATCH",
          credentials: "same-origin",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ type: "incorrect" }),
        });
        reqs.push(req);
      }
      Promise.all(reqs).then((_responses) => {
        window.location.reload();
      });
    },
  });
}

function showFlagsToggle(_event) {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.has("full")) {
    urlParams.delete("full");
  } else {
    urlParams.set("full", "true");
  }
  window.location.href = `${window.location.pathname}?${urlParams.toString()}`;
}

function showFlag(event) {
  let target = $(event.currentTarget);
  let eye = target.find("i");
  let flag = target.parent().find("pre");
  if (!flag.hasClass("full-flag")) {
    flag.text(flag.attr("title"));
    flag.addClass("full-flag");
    eye.addClass("fa-eye-slash");
    eye.removeClass("fa-eye");
  } else {
    flag.text(flag.attr("title").substring(0, 42) + "...");
    flag.removeClass("full-flag");
    eye.addClass("fa-eye");
    eye.removeClass("fa-eye-slash");
  }
}

function copyFlag(event) {
  let target = $(event.currentTarget);
  let flag = target.parent().find("pre");
  let text = flag.attr("title");
  navigator.clipboard.writeText(text);

  $(event.currentTarget).tooltip({
    title: "Copied!",
    trigger: "manual",
  });
  $(event.currentTarget).tooltip("show");

  setTimeout(function () {
    $(event.currentTarget).tooltip("hide");
  }, 1500);
}

function updateSubmissionVerified(event) {
  const target = $(event.currentTarget);
  const submissionId = target.data("submission-verified-id");
  const verified = target.prop("checked");

  target.prop("disabled", true);

  CTFd.fetch(`/api/v1/submissions/${submissionId}`, {
    method: "PATCH",
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ verified }),
  })
    .then((response) => response.json())
    .then((response) => {
      if (!response.success) {
        target.prop("checked", !verified);
      }
    })
    .catch(() => {
      target.prop("checked", !verified);
    })
    .finally(() => {
      target.prop("disabled", false);
    });
}

function setSolverPreviewContent(filename, content) {
  const code = document.getElementById("solver-preview-code");
  const language = getSolverLanguage(filename);
  const languageLabel = getSolverLanguageLabel(language);

  code.removeAttribute("data-highlighted");
  code.className = "";
  code.textContent = content;
  $("#solver-preview-language").text(languageLabel);

  if (language && language !== "plaintext" && hljs.getLanguage(language)) {
    code.classList.add(`language-${language}`);
    hljs.highlightElement(code);
  } else {
    code.classList.add("nohighlight");
  }
}

function bindAiSourceTooltips() {
  $(".submission-ai-source-link")
    .tooltip("dispose")
    .tooltip({
      boundary: "window",
      container: "body",
      fallbackPlacement: ["top"],
      placement: "top",
    });
}

function previewSolver(event) {
  event.preventDefault();

  const target = $(event.currentTarget);
  const solverUrl = target.data("solver-url");
  const solverName = target.data("solver-name") || "solver";

  $("#solver-preview-title").text(solverName);
  $("#solver-preview-download").attr("href", solverUrl);
  setSolverPreviewContent(solverName, "Loading...");
  $("#solver-preview-modal").modal("show");

  CTFd.fetch(solverUrl, {
    method: "GET",
    credentials: "same-origin",
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Unable to load solver file.");
      }
      return response.text();
    })
    .then((content) => {
      setSolverPreviewContent(solverName, content);
    })
    .catch(() => {
      setSolverPreviewContent(solverName, "Unable to load solver file.");
    });
}

$(() => {
  $("#show-full-flags-button").click(showFlagsToggle);
  $("#show-short-flags-button").click(showFlagsToggle);
  $(".show-flag").click(showFlag);
  $(".copy-flag").click(copyFlag);
  $("#correct-flags-button").click(correctSubmissions);
  $("#incorrect-flags-button").click(incorrectSubmissions);
  $(".delete-correct-submission").click(deleteCorrectSubmission);
  $("#submission-delete-button").click(deleteSelectedSubmissions);
  $(".submission-verified-checkbox").change(updateSubmissionVerified);
  $(".solver-preview-button").click(previewSolver);
  bindAiSourceTooltips();
});
