import * as React from "react";
import { Button } from "../Button";
import { Input } from "../Input";
import { Textarea } from "../Textarea";
import { api } from '../../lib/api.ts';
import { useState } from "react";

type Props = { open: boolean; onOpenChange: (v: boolean) => void; onCreated: () => void; };

export function PipelineCreateModal({ open, onOpenChange, onCreated }: Props) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function handleCreate() {
    setErr(null);
    if (!name.trim()) { setErr("Pipeline name is required."); return; }
    setLoading(true);
    try {
      await api.post("/pipelines/", { name, description });
      onOpenChange(false);
      setName(""); setDescription("");
      onCreated();
    } catch (e: any) {
      setErr(e.message || "Failed to create pipeline.");
    } finally {
      setLoading(false);
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/60 backdrop-blur-[2px]" onClick={() => onOpenChange(false)} />
      
      <div className="relative bg-white rounded-xl shadow-2xl p-6 w-full max-w-lg mx-4">
        <div className="mb-4">
          <h2 className="text-xl font-semibold">Create New Pipeline</h2>
          <p className="text-gray-600 text-sm">Add a new sales pipeline to your CRM system</p>
        </div>

        {err && <div className="text-red-600 text-sm mb-4 p-2 bg-red-50 rounded">{err}</div>}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Pipeline Name*</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Enter pipeline name" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea 
              value={description} 
              onChange={(e) => setDescription(e.target.value)} 
              placeholder="Describe this pipeline..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[80px]"
            />
          </div>
        </div>

        <div className="flex justify-end space-x-2 mt-6">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>Cancel</Button>
          <Button onClick={handleCreate} disabled={loading}>
            {loading ? "Creating…" : "Create Pipeline"}
          </Button>
        </div>
      </div>
    </div>
  );
}
