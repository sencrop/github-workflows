{ pkgs, ... }:

{
  packages = with pkgs; [
    actionlint
    yamllint
  ];
}
