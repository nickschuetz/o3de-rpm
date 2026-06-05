# Discord reply -> Nick_L (QT6 Support thread): deleteLater sweep result

> Follow-up to his #19819 TrackView find. One paragraph, paste as-is.
> Sweep method and triage detail below the divider in case he asks.

---

Prompted by your #19819 find, I ran a mechanical sweep of all 69 deleteLater() call sites in Code/ and Gems/ on development, classifying each receiver by whether it can be null at the call. One more real instance of the exact same shape: LyShine's UI Animation editor, Gems/LyShine/Code/Editor/Animation/UiAnimViewDopeSheetBase.cpp lines 538 and 546. It's a code clone of TrackViewDopeSheetBase: the constructor sets m_rubberBand to 0, only MouseMoveSelect creates it, and both select branches of OnLButtonUp call m_rubberBand->deleteLater() unguarded, so click-without-drag in the dope sheet should crash on Qt6 the same way (code-identical path, though I haven't runtime-repro'd this one). Everything else unguarded in the sweep turned out to be fresh locals, loop variables, or constructor-created members. Happy to put up the mirror fix if you'd like, or it could fold into #19819 since it's the same one-line guard.

---

## (Not part of the post) Sweep detail for Nick

- Method: `git grep -- '->deleteLater()'` on `upstream/development` over `Code/` + `Gems/` (69 sites), then a script classifying each receiver by presence of a null-guard (`if`/`while`/`&&`/`!= nullptr`) within the preceding 6 lines. 39 flagged unguarded, then manual triage.
- Triage outcomes:
  - Majority: fresh locals, loop variables, iterator derefs -- non-null by construction.
  - Ctor-created members (EMotionFX MotionSetMotionIdHandler x4, OpenParticleSystem ComboBoxWidget/EventHandlerWidget/PropertyEditorWidget x5) -- non-null for object lifetime.
  - One false positive: PropertyEditorAPI_Internals.h m_widget is guarded by `if (m_widget)` ~17 lines up, outside the script's context window.
  - ActorJointBrowseEdit m_jointSelectionWindow: deleteLater only fires inside the dialog's own finished lambda, non-null when it runs.
  - MysticQt DialogStack m_dialogWidget: non-null by construction when the dialog is found in the stack.
  - **Real: LyShine UiAnimViewDopeSheetBase.cpp:538,546** -- ctor `m_rubberBand = 0` (line 89), creation only in MouseMoveSelect (line 1335), both OnLButtonUp select branches call unguarded. Verified #19819's file list touches only Code/Editor/TrackView/TrackViewDopeSheetBase.cpp, so the clone is not covered.
- Evidence level: structural clone CONFIRMED by code read; the runtime crash on Qt6 is inferred from the identical path (not live-repro'd, and the reply says so).
- If he says "put up the fix": mirror #19819's guard at both LyShine sites, branch off development, DCO sign-off, ASCII-only, wait for Nick's explicit go before `gh pr create`.
