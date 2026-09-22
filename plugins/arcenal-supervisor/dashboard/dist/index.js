(function () {
  "use strict";
  const SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK || !window.__HERMES_PLUGINS__) return;
  const React = SDK.React;
  const h = React.createElement;

  function api(path, options) {
    return SDK.fetchJSON("/api/plugins/arcenal-supervisor" + path, options);
  }

  function formatBytes(value) {
    if (!value) return "0 Go";
    return (value / 1073741824).toFixed(1).replace(".", ",") + " Go";
  }

  function Metric(props) {
    return h("article", { className: "as-metric" },
      h("span", null, props.label),
      h("strong", null, props.value),
      h("small", null, props.detail || "")
    );
  }

  function SupervisorPage() {
    const state = React.useState(null);
    const data = state[0];
    const setData = state[1];
    const errorState = React.useState("");
    const error = errorState[0];
    const setError = errorState[1];
    const busyState = React.useState(false);
    const busy = busyState[0];
    const setBusy = busyState[1];
    const maintenanceState = React.useState(null);
    const maintenance = maintenanceState[0];
    const setMaintenance = maintenanceState[1];
    const pendingState = React.useState(null);
    const pending = pendingState[0];
    const setPending = pendingState[1];
    const serviceState = React.useState("arcenal");
    const selectedService = serviceState[0];
    const setSelectedService = serviceState[1];
    const resultState = React.useState(null);
    const maintenanceResult = resultState[0];
    const setMaintenanceResult = resultState[1];

    function refresh() {
      setBusy(true);
      setError("");
      api("/overview").then(setData).catch(function (err) {
        setError(err.message || "Supervision indisponible");
      }).finally(function () { setBusy(false); });
    }

    function createReport() {
      setBusy(true);
      api("/reports", { method: "POST" }).then(function (report) {
        setData(report);
      }).catch(function (err) {
        setError(err.message || "Rapport non créé");
      }).finally(function () { setBusy(false); });
    }

    function loadMaintenance() {
      api("/maintenance").then(setMaintenance).catch(function (err) {
        setError(err.message || "Catalogue de maintenance indisponible");
      });
    }

    function prepareMaintenance(action) {
      setPending(action);
      setMaintenanceResult(null);
      if (action.id !== "restart-service") setSelectedService("arcenal");
    }

    function executeMaintenance() {
      const payload = { operation: pending.id, confirmed: true };
      if (pending.id === "restart-service") payload.service = selectedService;
      setBusy(true);
      setError("");
      api("/maintenance/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }).then(function (result) {
        setMaintenanceResult(result);
        setData(result.overview);
        setPending(null);
      }).catch(function (err) {
        setError(err.message || "Intervention non exécutée");
      }).finally(function () { setBusy(false); });
    }

    React.useEffect(function () { refresh(); loadMaintenance(); }, []);

    return h("main", { className: "as-page" },
      h("header", { className: "as-heading" },
        h("div", null,
          h("p", null, "ARCENAL SYSTÈME"),
          h("h1", null, "Supervision générale"),
          h("span", null, "État, incidents et comptes rendus du serveur d’auto-hébergement.")
        ),
        h("div", { className: "as-actions" },
          h("button", { onClick: refresh, disabled: busy }, busy ? "Analyse…" : "Actualiser"),
          h("button", { className: "primary", onClick: createReport, disabled: busy }, "Créer un rapport")
        )
      ),
      error && h("div", { className: "as-error", role: "alert" }, error),
      !data && !error && h("div", { className: "as-loading" }, "Lecture de l’état du système…"),
      data && h(React.Fragment, null,
        h("section", { className: "as-health " + data.health },
          h("span", { className: "as-health-dot" }),
          h("div", null,
            h("strong", null, data.health === "healthy" ? "Système opérationnel" : "Attention requise"),
            h("small", null, data.platform.hostname + " · relevé " + new Date(data.generated_at).toLocaleString("fr-FR"))
          )
        ),
        h("section", { className: "as-metrics", "aria-label": "Ressources" },
          h(Metric, { label: "Disque système", value: data.resources.disk.percent + " %", detail: formatBytes(data.resources.disk.used) + " utilisés" }),
          h(Metric, { label: "Mémoire", value: data.resources.memory.percent + " %", detail: formatBytes(data.resources.memory.used) + " utilisés" }),
          h(Metric, { label: "Charge", value: data.resources.load[0], detail: "moyenne sur 1 minute" }),
          h(Metric, { label: "Incidents", value: data.incidents.length, detail: data.incidents.length ? "à examiner" : "aucun incident détecté" })
        ),
        h("section", { className: "as-panel" },
          h("div", { className: "as-section-title" }, h("h2", null, "Services critiques"), h("span", null, data.services.filter(function (s) { return s.healthy; }).length + "/" + data.services.length + " actifs")),
          h("div", { className: "as-services" }, data.services.map(function (service) {
            return h("article", { key: service.id },
              h("span", { className: "as-service-dot " + (service.healthy ? "ok" : "ko") }),
              h("div", null, h("strong", null, service.label), h("small", null, service.id)),
              h("b", null, service.state)
            );
          }))
        ),
        h("section", { className: "as-panel" },
          h("div", { className: "as-section-title" }, h("h2", null, "Incidents et recommandations")),
          data.incidents.length === 0
            ? h("p", { className: "as-empty" }, "Aucun incident détecté lors de ce relevé.")
            : h("div", { className: "as-incidents" }, data.incidents.map(function (incident, index) {
                return h("article", { key: incident.source + index }, h("strong", null, incident.source), h("span", null, incident.message));
              }))
        ),
        maintenance && h("section", { className: "as-panel" },
          h("div", { className: "as-section-title" },
            h("h2", null, "Maintenance sécurisée"),
            h("span", null, maintenance.execution_enabled ? "canal disponible" : "canal indisponible")
          ),
          h("div", { className: "as-maintenance" }, maintenance.actions.map(function (action) {
            return h("article", { key: action.id },
              h("div", null,
                h("strong", null, action.label),
                h("small", null, action.description),
                h("span", { className: "as-risk " + action.risk }, "Risque " + action.risk)
              ),
              h("button", {
                disabled: busy || !maintenance.execution_enabled,
                onClick: function () { prepareMaintenance(action); }
              }, "Préparer")
            );
          })),
          pending && h("div", { className: "as-confirm", role: "alertdialog", "aria-modal": "true" },
            h("strong", null, "Confirmer l’intervention"),
            h("p", null, pending.label + " — ARC vérifiera l’état du serveur après l’exécution."),
            pending.id === "restart-service" && h("label", null, "Service",
              h("select", { value: selectedService, onChange: function (event) { setSelectedService(event.target.value); } },
                data.services.map(function (service) {
                  return h("option", { key: service.id, value: service.id }, service.label);
                })
              )
            ),
            h("div", { className: "as-confirm-actions" },
              h("button", { disabled: busy, onClick: function () { setPending(null); } }, "Annuler"),
              h("button", { className: "primary", disabled: busy, onClick: executeMaintenance }, busy ? "Intervention…" : "Confirmer et exécuter")
            )
          ),
          maintenanceResult && h("div", { className: "as-maintenance-result", role: "status" },
            h("strong", null, "Intervention terminée"),
            h("span", null, maintenanceResult.action.label),
            maintenanceResult.details && h("pre", null, maintenanceResult.details)
          )
        )
      )
    );
  }

  window.__HERMES_PLUGINS__.register("arcenal-supervisor", SupervisorPage);
})();
