import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { assignUserRole, listAccessUsers, revokeUserRole, updateAccessUserStatus } from "../api/client";
import type { UserStatus } from "../api/types";

export function RoleManagementPage() {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["access-users"], queryFn: listAccessUsers });
  const mutation = useMutation({
    mutationFn: ({ userId, role, assigned }: { userId: string; role: string; assigned: boolean }) =>
      assigned ? revokeUserRole(userId, role) : assignUserRole(userId, role),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["access-users"] }),
  });
  const statusMutation = useMutation({
    mutationFn: ({ userId, status }: { userId: string; status: Exclude<UserStatus, "DELETION_PENDING"> }) =>
      updateAccessUserStatus(userId, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["access-users"] }),
  });

  if (query.isLoading) return <p>Loading access management...</p>;
  if (query.error) return <p role="alert">{query.error.message}</p>;

  return (
    <div className="stack">
      <dl className="debug-grid">
        {query.data?.statistics.map((statistic) => (
          <div key={statistic.role}>
            <dt>{statistic.role}</dt>
            <dd>{statistic.userCount} users</dd>
          </div>
        ))}
      </dl>
      {query.data?.items.map((user) => (
        <article key={user.id} className="debug-card">
          <h3>{user.email}</h3>
          <p>{user.id}</p>
          <p>Status: {user.status}</p>
          <div className="button-row">
            {query.data.availableRoles.map((role) => {
              const assigned = user.roles.includes(role.value);
              return (
                <button
                  key={role.value}
                  type="button"
                  disabled={mutation.isPending}
                  onClick={() => mutation.mutate({ userId: user.id, role: role.value, assigned })}
                >
                  {assigned ? `Revoke ${role.label}` : `Assign ${role.label}`}
                </button>
              );
            })}
          </div>
          {user.status === "ACTIVE" ? (
            <button
              type="button"
              className="danger-button"
              disabled={statusMutation.isPending}
              onClick={() => statusMutation.mutate({ userId: user.id, status: "DEACTIVATED" })}
            >
              Deactivate
            </button>
          ) : null}
          {user.status === "DEACTIVATED" ? (
            <button
              type="button"
              disabled={statusMutation.isPending}
              onClick={() => statusMutation.mutate({ userId: user.id, status: "ACTIVE" })}
            >
              Activate
            </button>
          ) : null}
        </article>
      ))}
      {statusMutation.error ? <p role="alert">{statusMutation.error.message}</p> : null}
    </div>
  );
}
