import{$ as a,B as g,C as w,z as r}from"./main-CA4_OjGq.js";const d=window.POST_REVOKE_CALC||{};let u=null;const v={};function R(){const t=new URLSearchParams;d.bracketId&&t.set("bracket_id",d.bracketId),d.sort&&t.set("sort",d.sort);const e=t.toString();return e?`?${e}`:""}function m(t){return`/api/v1/post-revoke-calc${t}${R()}`}function c(t,e){a("#post-revoke-status").text(t||"").toggleClass("text-danger",!!e).toggleClass("text-muted",!e)}function l(t){if(!t||!t.errors)return"Post-Revoke Calc update failed.";const e=[];return Object.keys(t.errors).forEach(o=>{const s=t.errors[o];Array.isArray(s)?e.push(s.join(`
`)):e.push(String(s))}),e.join(`
`)||"Post-Revoke Calc update failed."}function y(t,e){return w.fetch(t,{credentials:"same-origin",headers:{Accept:"application/json","Content-Type":"application/json"},...e}).then(o=>o.json())}function x(t,e){return c("Saving..."),y(t,{method:"PATCH",body:JSON.stringify(e)}).then(o=>{if(!o.success)throw o;return c("Saved."),o.data})}function T(t){t.forEach(e=>{const o=a(`[data-account-row="${e.account_id}"]`);if(!o.length)return;o.find("[data-rank]").text(e.rank),o.find("[data-pre-score]").text(e.pre_score_display),o.find("[data-post-score]").text(e.post_score_display),o.find("[data-score-diff]").text(e.score_delta_display).removeClass("score-diff-positive score-diff-negative score-diff-zero").addClass(`score-diff-${e.score_delta_class||"zero"}`),o.find("[data-solve-count]").text(e.solve_count_display).toggleClass("post-revoke-solve-count-high",!!e.high_solve_count);const s=o.find(".post-revoke-account-ban");s.prop("checked",e.calc_banned),s.prop("disabled",!d.canWrite||e.real_banned);const i=o.find(".post-revoke-account-note");i.is(":focus")||i.val(e.note||"")})}function E(t){t.forEach(e=>{const o=a(`[data-challenge-row="${e.challenge_id}"]`);o.length&&(o.find("[data-challenge-pre-score]").text(e.pre_score_display),o.find("[data-challenge-post-score]").text(e.post_score_display),o.find("[data-challenge-score-diff]").text(e.score_delta_display).removeClass("score-diff-positive score-diff-negative score-diff-zero").addClass(`score-diff-${e.score_delta_class||"zero"}`),o.find("[data-challenge-solve-count]").text(e.solve_count_display))})}function k(t){if(t==null||t==="")return"0";const e=Number(t);return Number.isInteger(e)?String(e):e.toFixed(2).replace(/0+$/,"").replace(/\.$/,"")}function O(t){const e=Number(t||0);return Number.isInteger(e)?String(e):e.toFixed(2).replace(/0+$/,"").replace(/\.$/,"")}function b(t,e){const o=t==="solves"?"Solves":"Awards",s=t==="solves"?"Challenge":"Award",i=t==="solves"?"No solves":"No awards";let p="";return e.length?p=e.map(n=>{const A=t==="solves"?n.challenge_name:n.name,N=n.revoked?"checked":"",f=d.canWrite?"":"disabled";return`
          <tr>
            <td class="col-name">${r(A||"")}</td>
            <td class="text-right col-score">${k(n.original_score)}</td>
            <td class="text-right col-score">${k(n.post_score)}</td>
            <td class="col-percent">
              <input type="number" min="0" max="100" step="0.01" class="form-control form-control-sm post-revoke-percent" data-kind="${t}" data-item-id="${n.id}" value="${O(n.percentage)}" ${f}>
            </td>
            <td class="text-center col-revoke">
              <input type="checkbox" class="post-revoke-item-revoke" data-kind="${t}" data-item-id="${n.id}" ${N} ${f}>
            </td>
            <td class="col-note">
              <textarea class="form-control form-control-sm post-revoke-note post-revoke-item-note" rows="1" data-kind="${t}" data-item-id="${n.id}" ${f}>${r(n.note||"")}</textarea>
            </td>
          </tr>
        `}).join(""):p=`<tr><td colspan="6" class="text-muted text-center">${i}</td></tr>`,`
    <h4 class="mt-3">${o}</h4>
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
        <tbody>${p}</tbody>
      </table>
    </div>
  `}function P(t){const e=t.metadata||{},o=[["Email",e.email],["Affiliation",e.affiliation],["Country",e.country]].filter(s=>s[1]);return o.length?`
    <div class="post-revoke-account-meta mt-2">
      ${o.map(([s,i])=>`
            <div class="post-revoke-account-meta-item">
              <span class="text-muted">${r(s)}</span>
              <strong>${r(i)}</strong>
            </div>
          `).join("")}
    </div>
  `:""}function j(t){const e=t.account;u=e.account_id,a("#post-revoke-detail-modal-title").text(e.name||"Post-Revoke Detail"),a("#post-revoke-detail-panel").html(`
    <div class="d-flex flex-wrap justify-content-between align-items-start">
      <div>
        <div class="text-muted post-revoke-detail-summary">
          <span>Rank <strong>${r(e.rank)}</strong></span>
          <span>Pre <strong>${r(e.pre_score_display)}</strong></span>
          <span>Post <strong>${r(e.post_score_display)}</strong></span>
          <span>Diff <strong class="score-diff-${e.score_delta_class||"zero"}">${r(e.score_delta_display)}</strong></span>
          <span>${r(e.bracket||"No bracket")}</span>
        </div>
        ${P(e)}
      </div>
      <div>
        ${e.calc_banned?'<span class="badge badge-danger">Banned</span>':'<span class="badge badge-success">Included</span>'}
      </div>
    </div>
    ${b("solves",t.solves)}
    ${b("awards",t.awards)}
  `)}function C(t,e=!0){return u=t,c("Loading detail..."),a("#post-revoke-detail-modal-title").text("Post-Revoke Detail"),a("#post-revoke-detail-panel").html('<div class="text-muted">Loading detail...</div>'),e&&a("#post-revoke-detail-modal").modal("show"),y(m(`/accounts/${t}`),{method:"GET"}).then(o=>{if(!o.success)throw o;j(o.data),c("")}).catch(o=>{c(l(o),!0),g({title:"Error!",body:l(o),button:"Okay"})})}function S(t){T(t.rows||[]),E(t.challenge_rows||[]),u&&C(u,!1)}function $(t,e){return x(m(`/accounts/${t}`),e).then(S).catch(o=>{c(l(o),!0),g({title:"Error!",body:l(o),button:"Okay"})})}function h(t,e,o){return x(m(`/${t}/${e}`),o).then(S).catch(s=>{c(l(s),!0),g({title:"Error!",body:l(s),button:"Okay"})})}function _(t,e){v[t]&&clearTimeout(v[t]),v[t]=setTimeout(e,600)}function I(t){const e=t==="challenges";a("#post-revoke-scoreboard-view").toggleClass("d-none",e),a("#post-revoke-challenge-view").toggleClass("d-none",!e),a("[data-post-revoke-view-button]").each(function(){const o=a(this),s=o.data("post-revoke-view-button")===t;o.toggleClass("active btn-primary",s).toggleClass("btn-outline-primary",!s).attr("aria-pressed",s?"true":"false")})}a(()=>{a("[data-post-revoke-view-button]").on("click",function(){I(a(this).data("post-revoke-view-button"))}),a("#post-revoke-summary-body").on("click",".post-revoke-detail-button",function(){C(a(this).data("account-id"))}),a("#post-revoke-summary-body").on("change",".post-revoke-account-ban",function(){const t=a(this);$(t.data("account-id"),{manual_banned:t.prop("checked")})}),a("#post-revoke-summary-body").on("input",".post-revoke-account-note",function(){const t=a(this),e=t.data("account-id");_(`account-${e}`,function(){$(e,{note:t.val()})})}),a("#post-revoke-detail-panel").on("change",".post-revoke-percent",function(){const t=a(this);h(t.data("kind"),t.data("item-id"),{percentage:t.val()})}),a("#post-revoke-detail-panel").on("change",".post-revoke-item-revoke",function(){const t=a(this);h(t.data("kind"),t.data("item-id"),{revoked:t.prop("checked")})}),a("#post-revoke-detail-panel").on("input",".post-revoke-item-note",function(){const t=a(this),e=`${t.data("kind")}-${t.data("item-id")}`;_(e,function(){h(t.data("kind"),t.data("item-id"),{note:t.val()})})}),a("#post-revoke-detail-modal").on("hidden.bs.modal",function(){u=null,a("#post-revoke-detail-modal-title").text("Post-Revoke Detail"),a("#post-revoke-detail-panel").html('<div class="text-muted">Loading detail...</div>')})});
