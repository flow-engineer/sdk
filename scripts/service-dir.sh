# Sourced by the check scripts: finds the private service checkout.
#
# FLOW_MESSAGING_DIR names the folder that holds the service (the folder with
# api/openapi.yaml, cmd/server and scripts/local-stack.sh). Unset, it defaults to
# ../flow-messaging beside this repo, and a missing default folder only skips the
# checks that need it. Set to a folder that does not exist, or to one without
# api/openapi.yaml, the calling script stops with an error naming the variable, so a
# wrong path never turns into a silent skip. A relative path is taken from the
# repo's root.
#
#   source "$root/scripts/service-dir.sh"
#   server=$(service_dir "$root")
service_dir() {
  local root=$1 dir
  if [ -z "${FLOW_MESSAGING_DIR:-}" ]; then
    echo "$root/../flow-messaging"
    return 0
  fi
  case "$FLOW_MESSAGING_DIR" in
    /*) dir=$FLOW_MESSAGING_DIR ;;
    *) dir="$root/$FLOW_MESSAGING_DIR" ;;
  esac
  if [ ! -d "$dir" ]; then
    echo "FLOW_MESSAGING_DIR is $FLOW_MESSAGING_DIR, but there is no folder at $dir." >&2
    echo "Set FLOW_MESSAGING_DIR to the service checkout's folder, or unset it to use ../flow-messaging." >&2
    return 1
  fi
  if [ ! -f "$dir/api/openapi.yaml" ]; then
    echo "FLOW_MESSAGING_DIR is $FLOW_MESSAGING_DIR, but $dir has no api/openapi.yaml, so it is not the service." >&2
    echo "Set FLOW_MESSAGING_DIR to the folder inside the checkout that holds the service." >&2
    return 1
  fi
  (cd "$dir" && pwd)
}
