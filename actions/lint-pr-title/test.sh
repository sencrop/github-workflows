PREFIXES="feat|fix|chore"
TITLE="feat(api): breaking change"
if [[ "$TITLE" =~ (^$PREFIXES)(\(.+\))?!?:.+$ ]]; then
  echo "Valid title $TITLE "
else
  echo "Invalid title $TITLE"
fi

# Should accept the ! before the :
PREFIXES="feat|fix|chore"
TITLE="feat(api)!: breaking change"
if [[ "$TITLE" =~ (^$PREFIXES)(\(.+\))?!?:.+$ ]]; then
  echo "Valid title $TITLE "
else
  echo "Invalid title $TITLE"
fi

# Should not accept the space before the :
PREFIXES="feat|fix|chore"
TITLE="feat(api) : breaking change"
if [[ "$TITLE" =~ (^$PREFIXES)(\(.+\))?!?:.+$ ]]; then
  echo "Valid title $TITLE "
else
  echo "Invalid title $TITLE"
fi
