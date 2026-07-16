import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";

import { assignUserRole, listAccessUsers, revokeUserRole, updateAccessUserStatus } from "../api/client";
import type { AccessUserListParams, UserStatus } from "../api/types";
import { PaginationControls } from "../components/PaginationControls";

const PAGE_LIMIT = 24;

function formatDate(value?: string | null): string {
  return value ? new Date(value).toLocaleString() : "-";
}

export function UsersPage() {
  const queryClient = useQueryClient();
  const [searchInput, setSearchInput] = useState("");
  const [queryText, setQueryText] = useState("");
  const [role, setRole] = useState("");
  const [status, setStatus] = useState<UserStatus | "">("");
  const [sortBy, setSortBy] = useState<NonNullable<AccessUserListParams["sortBy"]>>("updatedAt");
  const [sortOrder, setSortOrder] = useState<NonNullable<AccessUserListParams["sortOrder"]>>("desc");
  const [offset, setOffset] = useState(0);
  const queryParameters: AccessUserListParams = {
    q: queryText || undefined,
    role: role || undefined,
    status: status || undefined,
    sortBy,
    sortOrder,
    limit: PAGE_LIMIT,
    offset,
  };
  const query = useQuery({
    queryKey: ["access-users", queryParameters],
    queryFn: () => listAccessUsers(queryParameters),
    placeholderData: keepPreviousData,
  });
  const mutation = useMutation({
    mutationFn: ({ userId, role: changedRole, assigned }: { userId: string; role: string; assigned: boolean }) =>
      assigned ? revokeUserRole(userId, changedRole) : assignUserRole(userId, changedRole),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["access-users"] }),
  });
  const statusMutation = useMutation({
    mutationFn: ({ userId, status: changedStatus }: { userId: string; status: Exclude<UserStatus, "DELETION_PENDING"> }) =>
      updateAccessUserStatus(userId, changedStatus),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["access-users"] }),
  });

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    setOffset(0);
    setQueryText(searchInput.trim());
  }

  return (
    <section className="stack">
      <form className="inline-form" onSubmit={submitSearch}>
        <label>
          Search users
          <input
            type="search"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Email, user ID, or auth user ID"
          />
        </label>
        <button type="submit">Search</button>
      </form>

      <div className="inline-form">
        <label>
          Role
          <select
            value={role}
            onChange={(event) => {
              setRole(event.target.value);
              setOffset(0);
            }}
          >
            <option value="">All roles</option>
            {query.data?.availableRoles.map((availableRole) => (
              <option key={availableRole.value} value={availableRole.value}>{availableRole.label}</option>
            ))}
          </select>
        </label>
        <label>
          Status
          <select
            value={status}
            onChange={(event) => {
              setStatus(event.target.value as UserStatus | "");
              setOffset(0);
            }}
          >
            <option value="">All statuses</option>
            {query.data?.availableStatuses.map((availableStatus) => (
              <option key={availableStatus.value} value={availableStatus.value}>{availableStatus.label}</option>
            ))}
          </select>
        </label>
        <label>
          Sort by
          <select
            value={sortBy}
            onChange={(event) => {
              setSortBy(event.target.value as NonNullable<AccessUserListParams["sortBy"]>);
              setOffset(0);
            }}
          >
            <option value="updatedAt">Updated</option>
            <option value="createdAt">Created</option>
            <option value="email">Email</option>
          </select>
        </label>
        <label>
          Sort order
          <select
            value={sortOrder}
            onChange={(event) => {
              setSortOrder(event.target.value as NonNullable<AccessUserListParams["sortOrder"]>);
              setOffset(0);
            }}
          >
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </select>
        </label>
      </div>

      <dl className="debug-grid">
        {query.data?.statistics.map((statistic) => (
          <div key={statistic.role}>
            <dt>{statistic.role}</dt>
            <dd>{statistic.userCount} users</dd>
          </div>
        ))}
      </dl>

      {query.isLoading ? <p>Loading users...</p> : null}
      {query.error ? <p role="alert">{query.error.message}</p> : null}
      {query.data?.items.length === 0 ? <p>No users found.</p> : null}

      {query.data?.items.map((user) => (
        <article key={user.id} className="debug-card">
          <h3>{user.email}</h3>
          <dl className="debug-grid">
            <div><dt>User ID</dt><dd>{user.id}</dd></div>
            <div><dt>Auth user ID</dt><dd>{user.authUserId ?? "-"}</dd></div>
            <div><dt>Status</dt><dd>{user.status}</dd></div>
            <div><dt>Roles</dt><dd>{user.roles.length ? user.roles.join(", ") : "None"}</dd></div>
            <div><dt>Created</dt><dd>{formatDate(user.createdAt)}</dd></div>
            <div><dt>Updated</dt><dd>{formatDate(user.updatedAt)}</dd></div>
            <div><dt>Deletion requested</dt><dd>{formatDate(user.deletionRequestedAt)}</dd></div>
          </dl>
          <div className="button-row">
            {query.data.availableRoles.map((availableRole) => {
              const assigned = user.roles.includes(availableRole.value);
              return (
                <button
                  key={availableRole.value}
                  type="button"
                  disabled={mutation.isPending}
                  onClick={() => mutation.mutate({ userId: user.id, role: availableRole.value, assigned })}
                >
                  {assigned ? `Revoke ${availableRole.label}` : `Assign ${availableRole.label}`}
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
      {mutation.error ? <p role="alert">{mutation.error.message}</p> : null}
      {query.data ? (
        <PaginationControls
          total={query.data.total}
          limit={query.data.limit}
          offset={query.data.offset}
          onPage={setOffset}
        />
      ) : null}
    </section>
  );
}
