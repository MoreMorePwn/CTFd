import{$ as o,B as m,C as N,z as u}from"./main-CA4_OjGq.js";const i=window.POST_REVOKE_CALC||{};let l=null;const v={};function R(){const t=new URLSearchParams;i.bracketId&&t.set("bracket_id",i.bracketId),i.sort&&t.set("sort",i.sort);const e=t.toString();return e?`?${e}`:""}function g(t){return`/api/v1/post-revoke-calc${t}${R()}`}function r(t,e){o("#post-revoke-status").text(t||"").toggleClass("text-danger",!!e).toggleClass("text-muted",!e)}function d(t){if(!t||!t.errors)return"Post-Revoke Calc update failed.";const e=[];return Object.keys(t.errors).forEach(a=>{const n=t.errors[a];Array.isArray(n)?e.push(n.join(`
`)):e.push(String(n))}),e.join(`
`)||"Post-Revoke Calc update failed."}function _(t,e){return N.fetch(t,{credentials:"same-origin",headers:{Accept:"application/json","Content-Type":"application/json"},...e}).then(a=>a.json())}function x(t,e){return r("Saving..."),_(t,{method:"PATCH",body:JSON.stringify(e)}).then(a=>{if(!a.success)throw a;return r("Saved."),a.data})}function T(t){t.forEach(e=>{const a=o(`[data-account-row="${e.account_id}"]`);if(!a.length)return;a.find("[data-rank]").text(e.rank),a.find("[data-pre-score]").text(e.pre_score_display),a.find("[data-post-score]").text(e.post_score_display),a.find("[data-score-diff]").text(e.score_delta_display).removeClass("score-diff-positive score-diff-negative score-diff-zero").addClass(`score-diff-${e.score_delta_class||"zero"}`);const n=a.find(".post-revoke-account-ban");n.prop("checked",e.calc_banned),n.prop("disabled",!i.canWrite||e.real_banned);const c=a.find(".post-revoke-account-note");c.is(":focus")||c.val(e.note||"")})}function E(t){t.forEach(e=>{const a=o(`[data-challenge-row="${e.challenge_id}"]`);a.length&&(a.find("[data-challenge-pre-score]").text(e.pre_score_display),a.find("[data-challenge-post-score]").text(e.post_score_display),a.find("[data-challenge-score-diff]").text(e.score_delta_display).removeClass("score-diff-positive score-diff-negative score-diff-zero").addClass(`score-diff-${e.score_delta_class||"zero"}`),a.find("[data-challenge-solve-count]").text(e.solve_count_display))})}function k(t){if(t==null||t==="")return"0";const e=Number(t);return Number.isInteger(e)?String(e):e.toFixed(2).replace(/0+$/,"").replace(/\.$/,"")}function O(t){const e=Number(t||0);return Number.isInteger(e)?String(e):e.toFixed(2).replace(/0+$/,"").replace(/\.$/,"")}function b(t,e){const a=t==="solves"?"Solves":"Awards",n=t==="solves"?"Challenge":"Award",c=t==="solves"?"No solves":"No awards";let p="";return e.length?p=e.map(s=>{const A=t==="solves"?s.challenge_name:s.name,w=s.revoked?"checked":"",f=i.canWrite?"":"disabled";return`
          <tr>
            <td class="col-name">${u(A||"")}</td>
            <td class="text-right col-score">${k(s.original_score)}</td>
            <td class="text-right col-score">${k(s.post_score)}</td>
            <td class="col-percent">
              <input type="number" min="0" max="100" step="0.01" class="form-control form-control-sm post-revoke-percent" data-kind="${t}" data-item-id="${s.id}" value="${O(s.percentage)}" ${f}>
            </td>
            <td class="text-center col-revoke">
              <input type="checkbox" class="post-revoke-item-revoke" data-kind="${t}" data-item-id="${s.id}" ${w} ${f}>
            </td>
            <td class="col-note">
              <textarea class="form-control form-control-sm post-revoke-note post-revoke-item-note" rows="1" data-kind="${t}" data-item-id="${s.id}" ${f}>${u(s.note||"")}</textarea>
            </td>
          </tr>
        `}).join(""):p=`<tr><td colspan="6" class="text-muted text-center">${c}</td></tr>`,`
    <h4 class="mt-3">${a}</h4>
    <div class="table-responsive-lg">
      <table class="table table-sm table-striped border post-revoke-detail-table">
        <thead>
          <tr>
            <th class="col-name">${n}</th>
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
  `}function P(t){const e=t.metadata||{},a=[["Email",e.email],["Affiliation",e.affiliation],["Country",e.country]].filter(n=>n[1]);return a.length?`
    <div class="post-revoke-account-meta mt-2">
      ${a.map(([n,c])=>`
            <div class="post-revoke-account-meta-item">
              <span class="text-muted">${u(n)}</span>
              <strong>${u(c)}</strong>
            </div>
          `).join("")}
    </div>
  `:""}function j(t){const e=t.account;l=e.account_id,o("#post-revoke-detail-modal-title").text(e.name||"Post-Revoke Detail"),o("#post-revoke-detail-panel").html(`
    <div class="d-flex flex-wrap justify-content-between align-items-start">
      <div>
        <div class="text-muted">
          Rank ${e.rank} | Pre ${e.pre_score_display} | Post ${e.post_score_display} | Diff ${e.score_delta_display} | ${e.bracket||"No bracket"}
        </div>
        ${P(e)}
      </div>
      <div>
        ${e.calc_banned?'<span class="badge badge-danger">Banned</span>':'<span class="badge badge-success">Included</span>'}
      </div>
    </div>
    ${b("solves",t.solves)}
    ${b("awards",t.awards)}
  `)}function C(t,e=!0){return l=t,r("Loading detail..."),o("#post-revoke-detail-modal-title").text("Post-Revoke Detail"),o("#post-revoke-detail-panel").html('<div class="text-muted">Loading detail...</div>'),e&&o("#post-revoke-detail-modal").modal("show"),_(g(`/accounts/${t}`),{method:"GET"}).then(a=>{if(!a.success)throw a;j(a.data),r("")}).catch(a=>{r(d(a),!0),m({title:"Error!",body:d(a),button:"Okay"})})}function S(t){T(t.rows||[]),E(t.challenge_rows||[]),l&&C(l,!1)}function $(t,e){return x(g(`/accounts/${t}`),e).then(S).catch(a=>{r(d(a),!0),m({title:"Error!",body:d(a),button:"Okay"})})}function h(t,e,a){return x(g(`/${t}/${e}`),a).then(S).catch(n=>{r(d(n),!0),m({title:"Error!",body:d(n),button:"Okay"})})}function y(t,e){v[t]&&clearTimeout(v[t]),v[t]=setTimeout(e,600)}function I(t){const e=t==="challenges";o("#post-revoke-scoreboard-view").toggleClass("d-none",e),o("#post-revoke-challenge-view").toggleClass("d-none",!e),o("[data-post-revoke-view-button]").each(function(){const a=o(this),n=a.data("post-revoke-view-button")===t;a.toggleClass("active btn-primary",n).toggleClass("btn-outline-primary",!n).attr("aria-pressed",n?"true":"false")})}o(()=>{o("[data-post-revoke-view-button]").on("click",function(){I(o(this).data("post-revoke-view-button"))}),o("#post-revoke-summary-body").on("click",".post-revoke-detail-button",function(){C(o(this).data("account-id"))}),o("#post-revoke-summary-body").on("change",".post-revoke-account-ban",function(){const t=o(this);$(t.data("account-id"),{manual_banned:t.prop("checked")})}),o("#post-revoke-summary-body").on("input",".post-revoke-account-note",function(){const t=o(this),e=t.data("account-id");y(`account-${e}`,function(){$(e,{note:t.val()})})}),o("#post-revoke-detail-panel").on("change",".post-revoke-percent",function(){const t=o(this);h(t.data("kind"),t.data("item-id"),{percentage:t.val()})}),o("#post-revoke-detail-panel").on("change",".post-revoke-item-revoke",function(){const t=o(this);h(t.data("kind"),t.data("item-id"),{revoked:t.prop("checked")})}),o("#post-revoke-detail-panel").on("input",".post-revoke-item-note",function(){const t=o(this),e=`${t.data("kind")}-${t.data("item-id")}`;y(e,function(){h(t.data("kind"),t.data("item-id"),{note:t.val()})})}),o("#post-revoke-detail-modal").on("hidden.bs.modal",function(){l=null,o("#post-revoke-detail-modal-title").text("Post-Revoke Detail"),o("#post-revoke-detail-panel").html('<div class="text-muted">Loading detail...</div>')})});
