const config = require("@nicxe/semantic-release-config")({
  componentDir: "custom_components/krisinformation",
  manifestPath: "custom_components/krisinformation/manifest.json",
  projectName: "Krisinformation",
  repoSlug: "Nicxe/krisinformation"
}
);

const githubPlugin = config.plugins.find(
  (plugin) => Array.isArray(plugin) && plugin[0] === "@semantic-release/github"
);

if (githubPlugin?.[1]) {
  githubPlugin[1].successCommentCondition = false;
}

module.exports = config;
