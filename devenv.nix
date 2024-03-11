{ pkgs, ... }:

{
  packages = with pkgs; [
    awscli2
    aws-vault
    docker
  ];
}
