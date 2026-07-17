class DramatiqQueuePublisher:
    def publish_import_job(self, import_job_id: str) -> None:
        from app.imports.tasks import import_recipe_task

        import_recipe_task.send(import_job_id)

    def publish_recipe_embedding(self, recipe_id: str) -> None:
        from app.embeddings.tasks import embed_recipe_task

        embed_recipe_task.send(recipe_id)

    def publish_account_deletion(self, user_id: str) -> None:
        from app.users.tasks import delete_account_task

        delete_account_task.send(user_id)
