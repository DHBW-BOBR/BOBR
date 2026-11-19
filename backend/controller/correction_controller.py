class CorrectionController:
    def accept(self, issue_id: int):
        raise NotImplementedError

    def reject(self, issue_id: int):
        raise NotImplementedError
