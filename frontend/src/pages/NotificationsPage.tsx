import { useMutation, useQueryClient } from "@tanstack/react-query";

import { markAllNotificationsRead, patchNotification } from "../api/client";
import type { Notification } from "../api/types";

function formatDate(value?: string | null) {
  return value ? new Date(value).toLocaleString() : "";
}

function recipeIdForNotification(notification: Notification): string | null {
  if (notification.entityType === "recipe" && notification.entityId) return notification.entityId;
  const createdRecipeId = notification.data?.createdRecipeId;
  return typeof createdRecipeId === "string" ? createdRecipeId : null;
}

export function NotificationsPage({
  notifications,
  onOpenRecipe,
}: {
  notifications: Notification[];
  onOpenRecipe: (recipeId: string) => void;
}) {
  const queryClient = useQueryClient();
  const newestNotificationId = notifications[0]?.id;
  const hasUnreadNotifications = notifications.some((notification) => notification.status === "unread");
  const markReadMutation = useMutation({
    mutationFn: (notificationId: string) => patchNotification(notificationId, "read"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
  const markAllReadMutation = useMutation({
    mutationFn: (notificationId: string) => markAllNotificationsRead(notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  return (
    <section className="panel">
      <div className="section-heading">
        <h2>Notifications</h2>
        {hasUnreadNotifications && newestNotificationId ? (
          <button type="button" onClick={() => markAllReadMutation.mutate(newestNotificationId)} disabled={markAllReadMutation.isPending}>
            Mark all read
          </button>
        ) : null}
      </div>
      <div className="stack">
        {notifications.length ? (
          notifications.map((notification) => {
            const recipeId = recipeIdForNotification(notification);
            const isUnread = notification.status === "unread";
            return (
              <article key={notification.id} className={`notification-card ${isUnread ? "is-unread" : ""}`}>
                <div>
                  <strong>{notification.title}</strong>
                  <p>{notification.message}</p>
                  <small>
                    {notification.status}
                    {notification.createdAt ? ` - ${formatDate(notification.createdAt)}` : ""}
                  </small>
                </div>
                <div className="notification-actions">
                  {recipeId ? (
                    <button type="button" onClick={() => onOpenRecipe(recipeId)}>
                      Open recipe
                    </button>
                  ) : null}
                  {isUnread ? (
                    <button type="button" onClick={() => markReadMutation.mutate(notification.id)} disabled={markReadMutation.isPending}>
                      Mark read
                    </button>
                  ) : null}
                </div>
              </article>
            );
          })
        ) : (
          <p>No notifications yet.</p>
        )}
      </div>
    </section>
  );
}
