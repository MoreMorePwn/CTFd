import{$ as o,B as h,C as D,z as n}from"./main-3mOBuFOw.js";const i=window.POST_REVOKE_CALC||{};let p=null,u=null;const k={};function E(){const t=new URLSearchParams;i.bracketId&&t.set("bracket_id",i.bracketId),i.sort&&t.set("sort",i.sort);const e=t.toString();return e?`?${e}`:""}function g(t){return`/api/v1/post-revoke-calc${t}${E()}`}function r(t,e){o("#post-revoke-status").text(t||"").toggleClass("text-danger",!!e).toggleClass("text-muted",!e)}function d(t){if(!t||!t.errors)return"Post-Revoke Calc update failed.";const e=[];return Object.keys(t.errors).forEach(a=>{const s=t.errors[a];Array.isArray(s)?e.push(s.join(`
`)):e.push(String(s))}),e.join(`
`)||"Post-Revoke Calc update failed."}function $(t,e){return D.fetch(t,{credentials:"same-origin",headers:{Accept:"application/json","Content-Type":"application/json"},...e}).then(a=>a.json())}function C(t,e){return r("Saving..."),$(t,{method:"PATCH",body:JSON.stringify(e)}).then(a=>{if(!a.success)throw a;return r("Saved."),a.data})}function O(t){t.forEach(e=>{const a=o(`[data-account-row="${e.account_id}"]`);if(!a.length)return;a.find("[data-rank]").text(e.rank),a.find("[data-pre-score]").text(e.pre_score_display),a.find("[data-post-score]").text(e.post_score_display),a.find("[data-score-diff]").text(e.score_delta_display).removeClass("score-diff-positive score-diff-negative score-diff-zero").addClass(`score-diff-${e.score_delta_class||"zero"}`),a.find("[data-solve-count]").text(e.solve_count_display);const s=a.find(".post-revoke-account-ban");s.prop("checked",e.calc_banned),s.prop("disabled",!i.canWrite||e.real_banned);const l=a.find(".post-revoke-account-note");l.is(":focus")||l.val(e.note||"")})}function P(t){t.forEach(e=>{const a=o(`[data-challenge-row="${e.challenge_id}"]`);a.length&&(a.find("[data-challenge-pre-score]").text(e.pre_score_display),a.find("[data-challenge-post-score]").text(e.post_score_display),a.find("[data-challenge-score-diff]").text(e.score_delta_display).removeClass("score-diff-positive score-diff-negative score-diff-zero").addClass(`score-diff-${e.score_delta_class||"zero"}`),a.find("[data-challenge-solve-count]").text(e.solve_count_display))})}function f(t){if(t==null||t==="")return"0";const e=Number(t);return Number.isInteger(e)?String(e):e.toFixed(2).replace(/0+$/,"").replace(/\.$/,"")}function S(t){const e=Number(t||0);return Number.isInteger(e)?String(e):e.toFixed(2).replace(/0+$/,"").replace(/\.$/,"")}function x(t,e){const a=t==="solves"?"Solves":"Awards",s=t==="solves"?"Challenge":"Award",l=t==="solves"?"No solves":"No awards";let v="";return e.length?v=e.map(c=>{const R=t==="solves"?c.challenge_name:c.name,T=c.revoked?"checked":"",m=i.canWrite?"":"disabled";return`
          <tr>
            <td class="col-name">${n(R||"")}</td>
            <td class="text-right col-score">${f(c.original_score)}</td>
            <td class="text-right col-score">${f(c.post_score)}</td>
            <td class="col-percent">
              <input type="number" min="0" max="100" step="0.01" class="form-control form-control-sm post-revoke-percent" data-kind="${t}" data-item-id="${c.id}" value="${S(c.percentage)}" ${m}>
            </td>
            <td class="text-center col-revoke">
              <input type="checkbox" class="post-revoke-item-revoke" data-kind="${t}" data-item-id="${c.id}" ${T} ${m}>
            </td>
            <td class="col-note">
              <textarea class="form-control form-control-sm post-revoke-note post-revoke-item-note" rows="1" data-kind="${t}" data-item-id="${c.id}" ${m}>${n(c.note||"")}</textarea>
            </td>
          </tr>
        `}).join(""):v=`<tr><td colspan="6" class="text-muted text-center">${l}</td></tr>`,`
    <h4 class="mt-3">${a}</h4>
    <div class="table-responsive-lg">
      <table class="table table-sm table-striped border post-revoke-detail-table">
        <thead>
          <tr>
            <th class="col-name">${s}</th>
            <th class="text-right col-score">Original</th>
            <th class="text-right col-score">After</th>
            <th class="col-percent">Score %</th>
            <th class="text-center col-revoke">Revoke</th>
            <th class="col-note">Note</th>
          </tr>
        </thead>
        <tbody>${v}</tbody>
      </table>
    </div>
  `}function j(t){const e=t.metadata||{},a=[["Email",e.email],["Affiliation",e.affiliation],["Country",e.country]].filter(s=>s[1]);return a.length?`
    <div class="post-revoke-account-meta mt-2">
      ${a.map(([s,l])=>`
            <div class="post-revoke-account-meta-item">
              <span class="text-muted">${n(s)}</span>
              <strong>${n(l)}</strong>
            </div>
          `).join("")}
    </div>
  `:""}function I(t){const e=t.account;p=e.account_id,u=null,o("#post-revoke-detail-modal-title").text(e.name||"Post-Revoke Detail"),o("#post-revoke-detail-panel").html(`
    <div class="d-flex flex-wrap justify-content-between align-items-start">
      <div>
        <div class="text-muted post-revoke-detail-summary">
          <span>Rank <strong>${n(e.rank)}</strong></span>
          <span>Pre <strong>${n(e.pre_score_display)}</strong></span>
          <span>Post <strong>${n(e.post_score_display)}</strong></span>
          <span>Diff <strong class="score-diff-${e.score_delta_class||"zero"}">${n(e.score_delta_display)}</strong></span>
          <span>${n(e.bracket||"No bracket")}</span>
        </div>
        ${j(e)}
      </div>
      <div>
        ${e.calc_banned?'<span class="badge badge-danger">Banned</span>':'<span class="badge badge-success">Included</span>'}
      </div>
    </div>
    ${x("solves",t.solves)}
    ${x("awards",t.awards)}
  `)}function z(t){const e=t.calc_banned?"badge-danger":"badge-success",a=t.calc_banned?"Banned":"Included",s=t.banned_reason?`<span class="d-block text-muted small mt-1">${n(t.banned_reason)}</span>`:"";return`<span class="badge ${e}">${a}</span>${s}`}function L(t){const e=i.canWrite?"":"disabled";let a="";return t.length?a=t.map(s=>{const l=s.revoked?"checked":"",v=s.calc_banned?"table-danger":"",c=s.bracket?`<span class="d-block text-muted small">${n(s.bracket)}</span>`:"";return`
          <tr class="${v}">
            <td class="col-account">
              <span>${n(s.name||"")}</span>
              ${c}
            </td>
            <td class="text-right col-score">${f(s.original_score)}</td>
            <td class="text-right col-score">${f(s.post_score)}</td>
            <td class="col-percent">
              <input type="number" min="0" max="100" step="0.01" class="form-control form-control-sm post-revoke-percent" data-kind="solves" data-item-id="${s.id}" value="${S(s.percentage)}" ${e}>
            </td>
            <td class="text-center col-revoke">
              <input type="checkbox" class="post-revoke-item-revoke" data-kind="solves" data-item-id="${s.id}" ${l} ${e}>
            </td>
            <td class="col-note">
              <textarea class="form-control form-control-sm post-revoke-note post-revoke-item-note" rows="1" data-kind="solves" data-item-id="${s.id}" ${e}>${n(s.note||"")}</textarea>
            </td>
            <td class="text-center col-banned">${z(s)}</td>
          </tr>
        `}).join(""):a='<tr><td colspan="7" class="text-muted text-center">No correct submissions</td></tr>',`
    <div class="table-responsive-lg">
      <table class="table table-sm table-striped border post-revoke-detail-table post-revoke-challenge-detail-table">
        <thead>
          <tr>
            <th class="col-account">User / Team Name</th>
            <th class="text-right col-score">Original</th>
            <th class="text-right col-score">After</th>
            <th class="col-percent">Score %</th>
            <th class="text-center col-revoke">Revoke</th>
            <th class="col-note">Note</th>
            <th class="text-center col-banned">Banned</th>
          </tr>
        </thead>
        <tbody>${a}</tbody>
      </table>
    </div>
  `}function B(t){const e=t.challenge;p=null,u=e.challenge_id,o("#post-revoke-detail-modal-title").text(e.name||"Challenge Detail"),o("#post-revoke-detail-panel").html(`
    <div class="d-flex flex-wrap justify-content-between align-items-start">
      <div>
        <div class="text-muted post-revoke-detail-summary">
          <span>Pre <strong>${n(e.pre_score_display||"0")}</strong></span>
          <span>Post <strong>${n(e.post_score_display||"0")}</strong></span>
          <span>Diff <strong class="score-diff-${e.score_delta_class||"zero"}">${n(e.score_delta_display||"0")}</strong></span>
          <span>Solves <strong>${n(e.solve_count_display||"0 / 0")}</strong></span>
          <span>${n(e.category||"No category")}</span>
        </div>
      </div>
    </div>
    <h4 class="mt-3">Correct Submissions</h4>
    ${L(t.solves||[])}
  `)}function w(t,e=!0){return p=t,u=null,r("Loading detail..."),o("#post-revoke-detail-modal-title").text("Post-Revoke Detail"),o("#post-revoke-detail-panel").html('<div class="text-muted">Loading detail...</div>'),e&&o("#post-revoke-detail-modal").modal("show"),$(g(`/accounts/${t}`),{method:"GET"}).then(a=>{if(!a.success)throw a;I(a.data),r("")}).catch(a=>{r(d(a),!0),h({title:"Error!",body:d(a),button:"Okay"})})}function N(t,e=!0){return p=null,u=t,r("Loading challenge detail..."),o("#post-revoke-detail-modal-title").text("Challenge Detail"),o("#post-revoke-detail-panel").html('<div class="text-muted">Loading detail...</div>'),e&&o("#post-revoke-detail-modal").modal("show"),$(g(`/challenges/${t}`),{method:"GET"}).then(a=>{if(!a.success)throw a;B(a.data),r("")}).catch(a=>{r(d(a),!0),h({title:"Error!",body:d(a),button:"Okay"})})}function A(t){O(t.rows||[]),P(t.challenge_rows||[]),p?w(p,!1):u&&N(u,!1)}function _(t,e){return C(g(`/accounts/${t}`),e).then(A).catch(a=>{r(d(a),!0),h({title:"Error!",body:d(a),button:"Okay"})})}function b(t,e,a){return C(g(`/${t}/${e}`),a).then(A).catch(s=>{r(d(s),!0),h({title:"Error!",body:d(s),button:"Okay"})})}function y(t,e){k[t]&&clearTimeout(k[t]),k[t]=setTimeout(e,600)}function q(t){const e=t==="challenges";o("#post-revoke-scoreboard-view").toggleClass("d-none",e),o("#post-revoke-challenge-view").toggleClass("d-none",!e),o("[data-post-revoke-view-button]").each(function(){const a=o(this),s=a.data("post-revoke-view-button")===t;a.toggleClass("active btn-primary",s).toggleClass("btn-outline-primary",!s).attr("aria-pressed",s?"true":"false")})}o(()=>{o("[data-post-revoke-view-button]").on("click",function(){q(o(this).data("post-revoke-view-button"))}),o("#post-revoke-summary-body").on("click",".post-revoke-detail-button",function(){w(o(this).data("account-id"))}),o("#post-revoke-challenge-body").on("click",".post-revoke-challenge-detail-button",function(){N(o(this).data("challenge-id"))}),o("#post-revoke-summary-body").on("change",".post-revoke-account-ban",function(){const t=o(this);_(t.data("account-id"),{manual_banned:t.prop("checked")})}),o("#post-revoke-summary-body").on("input",".post-revoke-account-note",function(){const t=o(this),e=t.data("account-id");y(`account-${e}`,function(){_(e,{note:t.val()})})}),o("#post-revoke-detail-panel").on("change",".post-revoke-percent",function(){const t=o(this);b(t.data("kind"),t.data("item-id"),{percentage:t.val()})}),o("#post-revoke-detail-panel").on("change",".post-revoke-item-revoke",function(){const t=o(this);b(t.data("kind"),t.data("item-id"),{revoked:t.prop("checked")})}),o("#post-revoke-detail-panel").on("input",".post-revoke-item-note",function(){const t=o(this),e=`${t.data("kind")}-${t.data("item-id")}`;y(e,function(){b(t.data("kind"),t.data("item-id"),{note:t.val()})})}),o("#post-revoke-detail-modal").on("hidden.bs.modal",function(){p=null,u=null,o("#post-revoke-detail-modal-title").text("Post-Revoke Detail"),o("#post-revoke-detail-panel").html('<div class="text-muted">Loading detail...</div>')})});
