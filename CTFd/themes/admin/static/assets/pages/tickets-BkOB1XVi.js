import{$ as e,z as o,B as v,C as h}from"./main-CA4_OjGq.js";const g=window.TICKETS_ADMIN||{},i={tickets:g.tickets||[],targets:g.targets||[],selectedStatus:g.selectedStatus||"all",selectedTarget:null,resolvingTicketId:null},$={pending:"Pending",ongoing:"Ongoing",resolved:"Resolve"},T={pending:"badge-warning",ongoing:"badge-info",resolved:"badge-success"};function d(t){v({title:"Error",body:o(t||"Ticket update failed."),button:"OK"})}function f(t,n,s){return h.fetch(t,{method:n,body:s?JSON.stringify(s):void 0}).then(a=>a.json().then(c=>{if(!a.ok||!c.success){const r=c.errors||{},b=Object.keys(r).map(u=>r[u].join?r[u].join(" "):r[u]).join(" ");throw new Error(b||"Ticket update failed.")}return c}))}function l(t,n){return`<span class="badge ${n}">${o(t)}</span>`}function y(t){const n=$[t.status]||t.status,s=T[t.status]||"badge-secondary";return l(n,s)}function w(t){const n=o(t.target_name||"-"),s=t.target_type==="team"?"Team":"User";return`
    <div class="font-weight-bold">${n}</div>
    <div class="text-muted small">${s} #${o(t.target_id||"")}</div>
  `}function C(t){return t.status==="pending"?`
      <button type="button" class="btn btn-sm btn-primary ticket-mark-ongoing" data-ticket-id="${t.id}">
        Ongoing
      </button>
    `:t.status==="ongoing"?`
      <button type="button" class="btn btn-sm btn-success ticket-open-resolve" data-ticket-id="${t.id}">
        Resolve
      </button>
    `:'<span class="text-muted">Final</span>'}function S(){return i.selectedStatus==="all"?i.tickets:i.tickets.filter(t=>t.status===i.selectedStatus)}function m(){const t=S(),n=t.map(s=>{const a=s.resolve_note?`<div class="ticket-resolve-preview">${o(s.resolve_note)}</div>`:'<span class="text-muted">-</span>';return`
      <tr data-ticket-id="${s.id}">
        <td class="col-id">${o(s.id)}</td>
        <td class="col-target">${w(s)}</td>
        <td class="col-message"><div class="ticket-message-preview">${s.html||""}</div></td>
        <td class="col-note">${a}</td>
        <td class="col-status">${y(s)}</td>
        <td class="col-action">${C(s)}</td>
      </tr>
    `});e("#tickets-table tbody").html(n.join("")),e("#tickets-empty").toggleClass("d-none",t.length>0),_()}function _(){e("[data-ticket-filter]").each(function(){const t=e(this),n=t.data("ticket-filter")===i.selectedStatus;t.toggleClass("btn-primary",n),t.toggleClass("btn-outline-primary",!n)})}function k(){const t=(e("#ticket-target-search").val()||"").toLowerCase(),s=i.targets.filter(a=>(a.name||"").toLowerCase().includes(t)||(a.email||"").toLowerCase().includes(t)||(a.affiliation||"").toLowerCase().includes(t)).map(a=>{const c=[];return a.bracket&&c.push(l(a.bracket,"badge-secondary")),a.hidden&&c.push(l("Hidden","badge-warning")),a.banned&&c.push(l("Banned","badge-danger")),`
      <button type="button" class="list-group-item list-group-item-action ticket-target-option" data-target-id="${a.id}">
        <span>
          <span class="ticket-target-name">${o(a.name||"")}</span>
          <span class="ticket-target-meta d-block">
            ${o(a.email||"No email")}
            ${a.affiliation?` - ${o(a.affiliation)}`:""}
          </span>
        </span>
        <span class="ticket-badges">${c.join("")}</span>
      </button>
    `});e("#ticket-target-list").html(s.join("")||'<div class="ticket-empty">No matching users or teams.</div>')}function p(t){const n=i.tickets.findIndex(s=>s.id===t.id);n===-1?i.tickets.unshift(t):i.tickets.splice(n,1,t),m()}function j(){e("#ticket-target-search").val(""),k(),e("#ticket-target-modal").modal("show")}function N(t){i.selectedTarget=t,e("#ticket-selected-target").text(t.name||""),e("#ticket-title").val(""),e("#ticket-message").val(""),e("#ticket-type-toast").prop("checked",!0),e("#ticket-sound").prop("checked",!0),e("#ticket-target-modal").modal("hide"),e("#ticket-create-modal").modal("show")}function O(t){if(t.preventDefault(),!i.selectedTarget){d("Choose a user or team first.");return}const n=e("#ticket-create-form");n.find("button[type=submit]").prop("disabled",!0),f("/api/v1/tickets","POST",{target_id:i.selectedTarget.id,title:e("#ticket-title").val(),message:e("#ticket-message").val(),notification_type:e("input[name=notification_type]:checked").val(),sound:e("#ticket-sound").is(":checked")}).then(s=>{i.selectedStatus="all",p(s.data),e("#ticket-create-modal").modal("hide")}).catch(s=>d(s.message)).finally(()=>{n.find("button[type=submit]").prop("disabled",!1)})}function I(t){f(`/api/v1/tickets/${t}`,"PATCH",{status:"ongoing"}).then(n=>p(n.data)).catch(n=>d(n.message))}function x(t){i.resolvingTicketId=t,e("#ticket-resolve-note").val(""),e("#ticket-resolve-modal").modal("show")}function A(t){t.preventDefault();const n=e("#ticket-resolve-note").val();f(`/api/v1/tickets/${i.resolvingTicketId}`,"PATCH",{status:"resolved",resolve_note:n}).then(s=>{p(s.data),e("#ticket-resolve-modal").modal("hide")}).catch(s=>d(s.message))}e(()=>{m(),k(),e("[data-ticket-filter]").on("click",function(){i.selectedStatus=e(this).data("ticket-filter"),m()}),e("#ticket-add-button").on("click",j),e("#ticket-target-search").on("input",k),e("#ticket-create-form").on("submit",O),e("#ticket-resolve-form").on("submit",A),e("#ticket-target-list").on("click",".ticket-target-option",function(){const t=Number(e(this).data("target-id")),n=i.targets.find(s=>s.id===t);n&&N(n)}),e("#tickets-table").on("click",".ticket-mark-ongoing",function(){I(e(this).data("ticket-id"))}),e("#tickets-table").on("click",".ticket-open-resolve",function(){x(e(this).data("ticket-id"))})});
