import{$ as o,B as g,C as N,z as h}from"./main-CA4_OjGq.js";const r=window.POST_REVOKE_CALC||{};let l=null;const f={};function T(){const t=new URLSearchParams;r.bracketId&&t.set("bracket_id",r.bracketId),r.sort&&t.set("sort",r.sort);const e=t.toString();return e?`?${e}`:""}function b(t){return`/api/v1/post-revoke-calc${t}${T()}`}function c(t,e){o("#post-revoke-status").text(t||"").toggleClass("text-danger",!!e).toggleClass("text-muted",!e)}function i(t){if(!t||!t.errors)return"Post-Revoke Calc update failed.";const e=[];return Object.keys(t.errors).forEach(a=>{const n=t.errors[a];Array.isArray(n)?e.push(n.join(`
`)):e.push(String(n))}),e.join(`
`)||"Post-Revoke Calc update failed."}function _(t,e){return N.fetch(t,{credentials:"same-origin",headers:{Accept:"application/json","Content-Type":"application/json"},...e}).then(a=>a.json())}function x(t,e){return c("Saving..."),_(t,{method:"PATCH",body:JSON.stringify(e)}).then(a=>{if(!a.success)throw a;return c("Saved."),a.data})}function O(t){t.forEach(e=>{const a=o(`[data-account-row="${e.account_id}"]`);if(!a.length)return;a.find("[data-rank]").text(e.rank),a.find("[data-pre-score]").text(e.pre_score_display),a.find("[data-post-score]").text(e.post_score_display),a.find("[data-score-diff]").text(e.score_delta_display).removeClass("score-diff-positive score-diff-negative score-diff-zero").addClass(`score-diff-${e.score_delta_class||"zero"}`);const n=a.find(".post-revoke-account-ban");n.prop("checked",e.calc_banned),n.prop("disabled",!r.canWrite||e.real_banned);const d=a.find(".post-revoke-account-note");d.is(":focus")||d.val(e.note||"")})}function E(t){t.forEach(e=>{const a=o(`[data-challenge-row="${e.challenge_id}"]`);a.length&&(a.find("[data-challenge-pre-score]").text(e.pre_score_display),a.find("[data-challenge-post-score]").text(e.post_score_display),a.find("[data-challenge-score-diff]").text(e.score_delta_display).removeClass("score-diff-positive score-diff-negative score-diff-zero").addClass(`score-diff-${e.score_delta_class||"zero"}`),a.find("[data-challenge-solve-count]").text(e.solve_count_display))})}function m(t){if(t==null||t==="")return"0";const e=Number(t);return Number.isInteger(e)?String(e):e.toFixed(2).replace(/0+$/,"").replace(/\.$/,"")}function I(t){const e=Number(t||0);return Number.isInteger(e)?String(e):e.toFixed(2).replace(/0+$/,"").replace(/\.$/,"")}function k(t,e){const a=t==="solves"?"Solves":"Awards",n=t==="solves"?"Challenge":"Award",d=t==="solves"?"No solves":"No awards";let u="";return e.length?u=e.map(s=>{const w=t==="solves"?s.challenge_name:s.name,A=s.revoked?"checked":"",p=r.canWrite?"":"disabled";return`
          <tr>
            <td class="col-name">${h(w||"")}</td>
            <td class="text-right col-score">${m(s.original_score)}</td>
            <td class="text-right col-score">${m(s.post_score)}</td>
            <td class="col-percent">
              <input type="number" min="0" max="100" step="0.01" class="form-control form-control-sm post-revoke-percent" data-kind="${t}" data-item-id="${s.id}" value="${I(s.percentage)}" ${p}>
            </td>
            <td class="text-center col-revoke">
              <input type="checkbox" class="post-revoke-item-revoke" data-kind="${t}" data-item-id="${s.id}" ${A} ${p}>
            </td>
            <td class="col-note">
              <textarea class="form-control form-control-sm post-revoke-note post-revoke-item-note" rows="1" data-kind="${t}" data-item-id="${s.id}" ${p}>${h(s.note||"")}</textarea>
            </td>
          </tr>
        `}).join(""):u=`<tr><td colspan="6" class="text-muted text-center">${d}</td></tr>`,`
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
        <tbody>${u}</tbody>
      </table>
    </div>
  `}function R(t){const e=t.account;l=e.account_id,o("#post-revoke-detail-panel").html(`
    <div class="d-flex flex-wrap justify-content-between align-items-start">
      <div>
        <h3 class="mb-1">${h(e.name)}</h3>
        <div class="text-muted">
          Rank ${e.rank} | Pre ${e.pre_score_display} | Post ${e.post_score_display} | Diff ${e.score_delta_display} | ${e.bracket||"No bracket"}
        </div>
      </div>
      <div>
        ${e.calc_banned?'<span class="badge badge-danger">Banned</span>':'<span class="badge badge-success">Included</span>'}
      </div>
    </div>
    ${k("solves",t.solves)}
    ${k("awards",t.awards)}
  `)}function C(t){return l=t,c("Loading detail..."),_(b(`/accounts/${t}`),{method:"GET"}).then(e=>{if(!e.success)throw e;R(e.data),c("")}).catch(e=>{c(i(e),!0),g({title:"Error!",body:i(e),button:"Okay"})})}function S(t){O(t.rows||[]),E(t.challenge_rows||[]),l&&C(l)}function $(t,e){return x(b(`/accounts/${t}`),e).then(S).catch(a=>{c(i(a),!0),g({title:"Error!",body:i(a),button:"Okay"})})}function v(t,e,a){return x(b(`/${t}/${e}`),a).then(S).catch(n=>{c(i(n),!0),g({title:"Error!",body:i(n),button:"Okay"})})}function y(t,e){f[t]&&clearTimeout(f[t]),f[t]=setTimeout(e,600)}function j(t){const e=t==="challenges";o("#post-revoke-scoreboard-view").toggleClass("d-none",e),o("#post-revoke-challenge-view").toggleClass("d-none",!e),o("[data-post-revoke-view-button]").each(function(){const a=o(this),n=a.data("post-revoke-view-button")===t;a.toggleClass("active btn-primary",n).toggleClass("btn-outline-primary",!n).attr("aria-pressed",n?"true":"false")})}o(()=>{o("[data-post-revoke-view-button]").on("click",function(){j(o(this).data("post-revoke-view-button"))}),o("#post-revoke-summary-body").on("click",".post-revoke-detail-button",function(){C(o(this).data("account-id"))}),o("#post-revoke-summary-body").on("change",".post-revoke-account-ban",function(){const t=o(this);$(t.data("account-id"),{manual_banned:t.prop("checked")})}),o("#post-revoke-summary-body").on("input",".post-revoke-account-note",function(){const t=o(this),e=t.data("account-id");y(`account-${e}`,function(){$(e,{note:t.val()})})}),o("#post-revoke-detail-panel").on("change",".post-revoke-percent",function(){const t=o(this);v(t.data("kind"),t.data("item-id"),{percentage:t.val()})}),o("#post-revoke-detail-panel").on("change",".post-revoke-item-revoke",function(){const t=o(this);v(t.data("kind"),t.data("item-id"),{revoked:t.prop("checked")})}),o("#post-revoke-detail-panel").on("input",".post-revoke-item-note",function(){const t=o(this),e=`${t.data("kind")}-${t.data("item-id")}`;y(e,function(){v(t.data("kind"),t.data("item-id"),{note:t.val()})})})});
