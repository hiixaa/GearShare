import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <section className="space-y-3 py-8">
      <h1 className="text-2xl font-bold">Page not found</h1>
      <p>There is nothing at this address.</p>
      <Link to="/" className="underline focus:outline-2 focus:outline-slate-900">Back to the catalogue</Link>
    </section>
  );
}
