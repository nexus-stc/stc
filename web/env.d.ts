/// <reference types="vite/client" />

import { IPFSHTTPClient } from "ipfs-http-client";
import { SearchService } from "@/services/summa";

declare module "@vue/runtime-core" {
  interface ComponentCustomProperties {
    ipfs: IPFSHTTPClient;
    search_service: SearchService;
  }
}

declare global {
  namespace NodeJS {
    interface ProcessEnv {
      GITHUB_AUTH_TOKEN: string;
      NODE_ENV: "development" | "production";
      PORT?: string;
      PWD: string;
    }
  }
}