import { Sparkles } from "lucide-react";
import type { FormEvent, ReactElement } from "react";
import type { ModelOptionsResponse, SkillInfo, ToolsetInfo } from "@/lib/api";
import type { AgentDraft } from "@/lib/arcenal-agents";

interface AgentFormProps {
  busy: boolean;
  catalog: { models: ModelOptionsResponse; skills: SkillInfo[]; toolsets: ToolsetInfo[] };
  draft: AgentDraft;
  mode: "create" | "edit";
  onChange: (draft: AgentDraft) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

export function ArcenalAgentForm(props: AgentFormProps): ReactElement {
  const { busy, catalog, draft, mode, onChange, onSubmit } = props;
  const update = (field: keyof AgentDraft, value: string): void => onChange({ ...draft, [field]: value });
  return (
    <form className="arc-agent-editor" onSubmit={onSubmit}>
      <IdentityFields draft={draft} disabled={mode === "edit"} update={update} />
      <ModelFields draft={draft} models={catalog.models} update={update} />
      <CapabilityFields draft={draft} skills={catalog.skills} toolsets={catalog.toolsets} onChange={onChange} />
      <TextField label="Identité et consignes" value={draft.identity} onChange={(value) => update("identity", value)} />
      <TextField label="Contexte propre à l’agent" value={draft.context} onChange={(value) => update("context", value)} />
      <TextField label="Directives propres à l’agent" value={draft.directives} onChange={(value) => update("directives", value)} />
      <TextField label="Mémoire isolée" value={draft.memory} onChange={(value) => update("memory", value)} />
      <button className="arc-primary-button" disabled={busy} type="submit">
        <Sparkles aria-hidden />{busy ? "Enregistrement…" : mode === "create" ? "Créer et spécialiser" : "Enregistrer l’agent"}
      </button>
    </form>
  );
}

function IdentityFields({ draft, disabled, update }: { draft: AgentDraft; disabled: boolean; update: UpdateField }): ReactElement {
  return (
    <>
      <Field disabled={disabled} label="Identifiant" value={draft.name} placeholder="veille-reglementaire" onChange={(value) => update("name", value)} />
      <Field label="Mission" value={draft.mission} placeholder="Surveiller les évolutions réglementaires…" onChange={(value) => update("mission", value)} />
    </>
  );
}

function ModelFields({ draft, models, update }: { draft: AgentDraft; models: ModelOptionsResponse; update: UpdateField }): ReactElement {
  const providers = models.providers ?? [];
  const selected = providers.find((provider) => provider.slug === draft.provider);
  return (
    <div className="arc-form-row">
      <SelectField label="Fournisseur" value={draft.provider} options={providers.map((provider) => provider.slug)} onChange={(value) => update("provider", value)} />
      <Field list="arc-agent-models" label="Modèle principal" value={draft.mainModel} placeholder="Choisir un modèle" onChange={(value) => update("mainModel", value)} />
      <Field list="arc-agent-models" label="Modèle secondaire" value={draft.secondaryModel} placeholder="Optionnel" onChange={(value) => update("secondaryModel", value)} />
      <datalist id="arc-agent-models">{(selected?.models ?? []).map((model) => <option key={model} value={model} />)}</datalist>
    </div>
  );
}

function CapabilityFields({ draft, skills, toolsets, onChange }: { draft: AgentDraft; skills: SkillInfo[]; toolsets: ToolsetInfo[]; onChange: (draft: AgentDraft) => void }): ReactElement {
  return (
    <div className="arc-agent-capability-grid">
      <Checklist title="Compétences" entries={skills.map((skill) => ({ label: skill.name, value: skill.name }))} selected={draft.skills} onChange={(values) => onChange({ ...draft, skills: values })} />
      <Checklist title="Outils autorisés" entries={toolsets.map((toolset) => ({ label: toolset.label, value: toolset.name }))} selected={draft.toolsets} onChange={(values) => onChange({ ...draft, toolsets: values })} />
    </div>
  );
}

function Checklist({ title, entries, selected, onChange }: ChecklistProps): ReactElement {
  return (
    <fieldset className="arc-agent-checklist"><legend>{title}</legend>
      <div>{entries.map((entry) => <label key={entry.value}><input type="checkbox" checked={selected.includes(entry.value)} onChange={() => onChange(toggle(selected, entry.value))} /><span>{entry.label}</span></label>)}</div>
    </fieldset>
  );
}

function Field({ disabled = false, label, list, value, placeholder, onChange }: FieldProps): ReactElement {
  return <label className="arc-field"><span>{label}</span><input disabled={disabled} list={list} value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} /></label>;
}

function SelectField({ label, value, options, onChange }: SelectFieldProps): ReactElement {
  return <label className="arc-field"><span>{label}</span><select value={value} onChange={(event) => onChange(event.target.value)}>{options.map((option) => <option key={option} value={option}>{option}</option>)}</select></label>;
}

function TextField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }): ReactElement {
  return <label className="arc-field"><span>{label}</span><textarea rows={5} value={value} onChange={(event) => onChange(event.target.value)} /></label>;
}

function toggle(values: string[], value: string): string[] {
  return values.includes(value) ? values.filter((entry) => entry !== value) : [...values, value];
}

type UpdateField = (field: keyof AgentDraft, value: string) => void;
interface FieldProps { disabled?: boolean; label: string; list?: string; value: string; placeholder: string; onChange: (value: string) => void }
interface SelectFieldProps { label: string; value: string; options: string[]; onChange: (value: string) => void }
interface ChecklistProps { title: string; entries: Array<{ label: string; value: string }>; selected: string[]; onChange: (values: string[]) => void }
