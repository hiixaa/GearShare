import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { EMPTY_ITEM, toRequestBody, validateItem } from "../lib/validateItem";

const input = "w-full rounded border border-slate-300 bg-white px-2 py-1.5";

/** One labelled input, with its error message underneath (Task 4.4). */
function Field({ name, label, form, errors, touched, onChange, onBlur, ...props }) {
  const showError = touched[name] && errors[name];
  return (
    <div>
      <label htmlFor={name} className="block text-sm font-medium">{label}</label>
      <input id={name} name={name} value={form[name]} onChange={onChange} onBlur={onBlur}
             aria-invalid={Boolean(showError)} aria-describedby={showError ? `${name}-error` : undefined}
             className={input} {...props} />
      {showError && <p id={`${name}-error`} className="mt-1 text-sm text-red-700">{errors[name]}</p>}
    </div>
  );
}

export default function AddItemPage() {
  const [form, setForm] = useState(EMPTY_ITEM);
  const [touched, setTouched] = useState({});
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState(null);   // {ok, text, sku}

  const errors = validateItem(form);
  const valid = Object.keys(errors).length === 0;

  // Controlled inputs: React state is the single source of truth for every field.
  const onChange = (e) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
    setTouched((t) => ({ ...t, [name]: true }));   // show the error while typing
  };
  const onBlur = (e) => setTouched((t) => ({ ...t, [e.target.name]: true }));
  const shared = { form, errors, touched, onChange, onBlur };

  const submit = async (e) => {
    e.preventDefault();
    if (!valid) return;
    setSaving(true);
    try {
      const item = await api("/gear", { method: "POST", body: toRequestBody(form) });
      setResult({ ok: true, text: `Added '${item.name}' to the catalogue.`, sku: item.sku });
      setForm(EMPTY_ITEM);       // success: the form clears
      setTouched({});
    } catch (err) {
      setResult({ ok: false, text: err.message });   // e.g. the SKU is already used
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="max-w-xl space-y-4">
      <h1 className="text-2xl font-bold">Add item (staff)</h1>
      <form onSubmit={submit} noValidate className="space-y-3 rounded-lg border border-slate-200 bg-white p-5">
        <Field name="sku" label="SKU (10 digits)" inputMode="numeric" {...shared} />
        <Field name="name" label="Name" {...shared} />
        <div className="grid gap-3 sm:grid-cols-2">
          <Field name="category" label="Category" placeholder="e.g. Lenses" {...shared} />
          <Field name="parent_category" label="Parent category (optional)" placeholder="e.g. Photography" {...shared} />
        </div>
        <div>
          <label htmlFor="item_type" className="block text-sm font-medium">Type</label>
          <select id="item_type" name="item_type" value={form.item_type} onChange={onChange} className={input}>
            <option>Equipment</option>
            <option>Accessory</option>
            <option>Display</option>
          </select>
        </div>
        <Field name="tags" label="Tags (comma-separated)" placeholder="photo, lens" {...shared} />
        <div className="grid gap-3 sm:grid-cols-3">
          <Field name="weight_g" label="Weight (g)" inputMode="numeric" {...shared} />
          <Field name="price" label="Price (₹)" inputMode="numeric" {...shared} />
          <Field name="total_units" label="Units" inputMode="numeric" {...shared} />
        </div>
        <button type="submit" disabled={!valid || saving}
                className="rounded bg-slate-900 px-4 py-2 font-semibold text-white focus:outline-2 focus:outline-offset-2 focus:outline-slate-900 disabled:cursor-not-allowed disabled:opacity-50">
          {saving ? "Saving..." : "Add item"}
        </button>
      </form>

      {result && (
        <p role={result.ok ? "status" : "alert"}
           className={`rounded p-3 ${result.ok ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}>
          {result.text}{" "}
          {result.ok && <Link to={`/gear/${result.sku}`} className="underline">View it</Link>}
        </p>
      )}
    </section>
  );
}
