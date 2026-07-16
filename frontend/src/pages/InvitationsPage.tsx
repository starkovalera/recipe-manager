import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";

import { createInvitation, listInvitations, revokeInvitation } from "../api/client";

export function InvitationsPage() {
  const [email, setEmail] = useState("");
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["invitations"], queryFn: listInvitations });
  const createMutation = useMutation({
    mutationFn: createInvitation,
    onSuccess: () => {
      setEmail("");
      return queryClient.invalidateQueries({ queryKey: ["invitations"] });
    },
  });
  const revokeMutation = useMutation({
    mutationFn: revokeInvitation,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["invitations"] }),
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedEmail = email.trim();
    if (normalizedEmail) createMutation.mutate(normalizedEmail);
  }

  if (query.isLoading) return <p>Loading invitations...</p>;
  if (query.error) return <p role="alert">{query.error.message}</p>;

  return (
    <div className="stack">
      <form className="debug-card stack" onSubmit={submit}>
        <h3>Invite user</h3>
        <label>
          Email
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        </label>
        <button type="submit" disabled={createMutation.isPending}>Send invitation</button>
        {createMutation.error ? <p role="alert">{createMutation.error.message}</p> : null}
      </form>
      {query.data?.items.map((invitation) => (
        <article key={invitation.id} className="debug-card">
          <div className="debug-card__header">
            <div>
              <h3>{invitation.email}</h3>
              <p>{invitation.status}</p>
            </div>
            {invitation.status === "PENDING" ? (
              <button
                type="button"
                className="danger-button"
                disabled={revokeMutation.isPending}
                aria-label={`Revoke ${invitation.email}`}
                onClick={() => revokeMutation.mutate(invitation.id)}
              >
                Revoke
              </button>
            ) : null}
          </div>
        </article>
      ))}
      {revokeMutation.error ? <p role="alert">{revokeMutation.error.message}</p> : null}
    </div>
  );
}
