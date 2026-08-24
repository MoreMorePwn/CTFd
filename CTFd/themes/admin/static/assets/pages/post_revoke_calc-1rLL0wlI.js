import{$ as o,B as m,C as T,z as v}from"./main-3mOBuFOw.js";const c=window.POST_REVOKE_CALC||{};let l=null;const f={};function O(){const t=new URLSearchParams;c.bracketId&&t.set("bracket_id",c.bracketId),c.sort&&t.set("sort",c.sort);const e=t.toString();return e?`?${e}`:""}function b(t){return`/api/v1/post-revoke-calc${t}${O()}`}function r(t,e){o("#post-revoke-status").text(t||"").toggleClass("text-danger",!!e).toggleClass("text-muted",!e)}function i(t){if(!t||!t.errors)return"Post-Revoke Calc update failed.";const e=[];return Object.keys(t.errors).forEach(a=>{const n=t.errors[a];Array.isArray(n)?e.push(n.join(`
`)):e.push(String(n))}),e.join(`
`)||"Post-Revoke Calc update failed."}function x(t,e){return T.fetch(t,{credentials:"same-origin",headers:{Accept:"application/json","Content-Type":"application/json"},...e}).then(a=>a.json())}function _(t,e){return r("Saving..."),x(t,{method:"PATCH",body:JSON.stringify(e)}).then(a=>{if(!a.success)throw a;return r("Saved."),a.data})}function I(t){t.forEach(e=>{const a=o(`[data-account-row="${e.account_id}"]`);if(!a.length)return;a.find("[data-rank]").text(e.rank),a.find("[data-pre-score]").text(e.pre_score_display),a.find("[data-post-score]").text(e.post_score_display),a.find("[data-score-diff]").text(e.score_delta_display).removeClass("score-diff-positive score-diff-negative score-diff-zero").addClass(`score-diff-${e.score_delta_class||"zero"}`);const n=a.find(".post-revoke-account-ban");n.prop("checked",e.calc_banned),n.prop("disabled",!c.canWrite||e.real_banned);const d=a.find(".post-revoke-account-note");d.is(":focus")||d.val(e.note||"")})}function k(t){if(t==null||t==="")return"0";const e=Number(t);return Number.isInteger(e)?String(e):e.toFixed(2).replace(/0+$/,"").replace(/\.$/,"")}function j(t){const e=Number(t||0);return Number.isInteger(e)?String(e):e.toFixed(2).replace(/0+$/,"").replace(/\.$/,"")}function g(t,e){const a=t==="solves"?"Solves":"Awards",n=t==="solves"?"Challenge":"Award",d=t==="solves"?"No solves":"No awards";let u="";return e.length?u=e.map(s=>{const N=t==="solves"?s.challenge_name:s.name,A=s.revoked?"checked":"",p=c.canWrite?"":"disabled";return`
          <tr>
            <td class="col-name">${v(N||"")}</td>
            <td class="text-right col-score">${k(s.original_score)}</td>
            <td class="text-right col-score">${k(s.post_score)}</td>
            <td class="col-percent">
              <input type="number" min="0" max="100" step="0.01" class="form-control form-control-sm post-revoke-percent" data-kind="${t}" data-item-id="${s.id}" value="${j(s.percentage)}" ${p}>
            </td>
            <td class="text-center col-revoke">
              <input type="checkbox" class="post-revoke-item-revoke" data-kind="${t}" data-item-id="${s.id}" ${A} ${p}>
            </td>
            <td class="col-note">
              <textarea class="form-control form-control-sm post-revoke-note post-revoke-item-note" rows="1" data-kind="${t}" data-item-id="${s.id}" ${p}>${v(s.note||"")}</textarea>
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
  `}function w(t){const e=t.account;l=e.account_id,o("#post-revoke-detail-panel").html(`
    <div class="d-flex flex-wrap justify-content-between align-items-start">
      <div>
        <h3 class="mb-1">${v(e.name)}</h3>
        <div class="text-muted">
          Rank ${e.rank} | Pre ${e.pre_score_display} | Post ${e.post_score_display} | Diff ${e.score_delta_display} | ${e.bracket||"No bracket"}
        </div>
      </div>
      <div>
        ${e.calc_banned?'<span class="badge badge-danger">Banned</span>':'<span class="badge badge-success">Included</span>'}
      </div>
    </div>
    ${g("solves",t.solves)}
    ${g("awards",t.awards)}
  `)}function S(t){return l=t,r("Loading detail..."),x(b(`/accounts/${t}`),{method:"GET"}).then(e=>{if(!e.success)throw e;w(e.data),r("")}).catch(e=>{r(i(e),!0),m({title:"Error!",body:i(e),button:"Okay"})})}function C(t){I(t.rows||[]),l&&S(l)}function $(t,e){return _(b(`/accounts/${t}`),e).then(C).catch(a=>{r(i(a),!0),m({title:"Error!",body:i(a),button:"Okay"})})}function h(t,e,a){return _(b(`/${t}/${e}`),a).then(C).catch(n=>{r(i(n),!0),m({title:"Error!",body:i(n),button:"Okay"})})}function y(t,e){f[t]&&clearTimeout(f[t]),f[t]=setTimeout(e,600)}o(()=>{o("#post-revoke-summary-body").on("click",".post-revoke-detail-button",function(){S(o(this).data("account-id"))}),o("#post-revoke-summary-body").on("change",".post-revoke-account-ban",function(){const t=o(this);$(t.data("account-id"),{manual_banned:t.prop("checked")})}),o("#post-revoke-summary-body").on("input",".post-revoke-account-note",function(){const t=o(this),e=t.data("account-id");y(`account-${e}`,function(){$(e,{note:t.val()})})}),o("#post-revoke-detail-panel").on("change",".post-revoke-percent",function(){const t=o(this);h(t.data("kind"),t.data("item-id"),{percentage:t.val()})}),o("#post-revoke-detail-panel").on("change",".post-revoke-item-revoke",function(){const t=o(this);h(t.data("kind"),t.data("item-id"),{revoked:t.prop("checked")})}),o("#post-revoke-detail-panel").on("input",".post-revoke-item-note",function(){const t=o(this),e=`${t.data("kind")}-${t.data("item-id")}`;y(e,function(){h(t.data("kind"),t.data("item-id"),{note:t.val()})})})});
