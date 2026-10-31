# Repository settings (one-time, by the owner)

These change the public repository's settings, so they're not done by a push.

**Topics** (make the repo findable on GitHub):

```bash
gh repo edit tomasstankovic/running-coach --add-topic claude --add-topic claude-skills --add-topic claude-plugin --add-topic running --add-topic training-plan --add-topic marathon --add-topic trainingpeaks --add-topic strava --add-topic hrv --add-topic sports-science
```

**Description and website**:

```bash
gh repo edit tomasstankovic/running-coach --description "Running coach for Claude: season plans, HRV check-ins, session analysis and research-backed load rules, from TrainingPeaks, Strava or a conversation." --homepage "https://github.com/tomasstankovic/running-coach#install"
```

**Social preview image**: *Settings → General → Social preview → Edit → Upload an image* and pick
`docs/img/social-preview.png` (1280 × 640). GitHub has no API for this.

**Discussions** (a place for questions and feedback that aren't bugs):

```bash
gh repo edit tomasstankovic/running-coach --enable-discussions
```
