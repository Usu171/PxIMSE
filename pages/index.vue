<template>
  <v-container>
    <v-row>
      <v-col cols="12" sm="6">
        <v-text-field
          v-model="inputText"
          clearable
          label="text"
          variant="outlined"
        ></v-text-field>
      </v-col>
      <v-col cols="12" sm="6">
        <v-file-input
          v-model="imageFile"
          label="Select Image"
          variant="outlined"
        ></v-file-input>
      </v-col>

      <v-col cols="6" sm="5">
        <v-combobox
          v-model="queryText"
          label="Query"
          dense
          outlined
          clearable
          chips
          multiple
          variant="outlined"
        ></v-combobox>
      </v-col>
      <v-col cols="6" sm="5">
        <v-combobox
          v-model="sortText"
          :items="[
            'filename',
            'folder',
            'type',
            'width',
            'height',
            'filesize',
            'date',
            'user',
            'userid',
            'illustid',
            'createDate',
            'viewCount',
            'bookmarkCount',
            'likeCount',
            'commentCount',
          ]"
          label="Sort"
          dense
          outlined
          clearable
          chips
          multiple
          variant="outlined"
        ></v-combobox>
      </v-col>
      <v-col cols="12" sm="2">
        <v-btn @click="submitData" block height="56px">Submit</v-btn>
      </v-col>
    </v-row>

    <v-lazy
      :min-height="200"
      :options="{ threshold: 0.5 }"
      transition="fade-transition"
    >
      <v-row>
        <v-col v-for="(item, index) in pagedData" :key="index" cols="12" sm="3">
          <v-card @click="openDialog(item)">
            <v-img
              :src="`${serverUrl}/${item.folder}/${item.filename}`"
              :alt="item.filename"
              height="250px"
            ></v-img>
            <v-card-title class="text-center">{{
              item.filename.split(".").slice(0, -1).join(".")
            }}</v-card-title>
            <v-card-subtitle v-if="item.image_distance">{{
              "image distance: " + item.image_distance.toFixed(8)
            }}</v-card-subtitle>
            <v-card-subtitle v-if="item.text_distance">{{
              "text distance: " + item.text_distance.toFixed(8)
            }}</v-card-subtitle>
          </v-card>
        </v-col>
      </v-row>
    </v-lazy>

    <v-dialog v-model="dialog" max-width="1200px" height="100%">
      <v-card
        ><a
          :href="`${serverUrl}/${selectedItem?.folder}/${selectedItem?.filename}`"
          target="_blank"
        >
          <v-img
            :src="`${serverUrl}/${selectedItem?.folder}/${selectedItem?.filename}`"
            height="900px"
          ></v-img
        ></a>

        <v-card-title>{{ selectedItem?.filename }}</v-card-title>
        <div v-for="(value, key) in selectedItem" :key="key">
          <v-card-text v-if="value" class="pa-1 pl-5">
            <span class="font-weight-bold text-body-1 mr-1">
              {{ key.charAt(0).toUpperCase() + key.slice(1) }}:
            </span>
            <span v-if="key === 'link'">
              <a
                v-if="selectedItem.link"
                :href="selectedItem.link"
                target="_blank"
                style="color: #007bff; font-size: 15px"
              >
                {{ selectedItem.link }}
              </a>
            </span>
            <span v-else style="font-size: 15px">{{ value }}</span>
          </v-card-text>
        </div>
        <v-card-actions>
          <v-btn @click="dialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-pagination
      v-if="pageCount > 1"
      v-model="currentPage"
      :length="pageCount"
      @click="scrollToTop"
    ></v-pagination>

    <v-snackbar v-model="snackbar.show" :timeout="2000" :color="snackbar.color">
      {{ snackbar.message }}
      <template v-slot:actions>
        <v-btn color="white" variant="text" @click="snackbar.show = false">
          Close
        </v-btn>
      </template>
    </v-snackbar>

  </v-container>
</template>

<script setup>
import { ref } from "vue";
import config from "../config.mjs";

const data = ref([]);
const inputText = ref(null);
const queryText = ref(null);
const sortText = ref(null);
const imageFile = ref(null);
const selectedItem = ref(null);
const dialog = ref(false);
const serverUrl = config.serverUrl;
const apiUrl = config.apiUrl;

const snackbar = ref({
  show: false,
  message: "",
  color: "success",
});

const currentPage = ref(1);
const itemsPerPage = ref(200);

const pageCount = computed(() => {
  return Math.ceil(data.value.length / itemsPerPage.value);
});

const pagedData = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value;
  const end = start + itemsPerPage.value;
  return data.value.slice(start, end);
});

const submitData = async () => {
  const formData = new FormData();
  formData.append("text", inputText.value);
  formData.append("query", queryText.value);
  formData.append("sort", sortText.value);
  if (imageFile.value) {
    formData.append("image", imageFile.value);
  }
  try {
    const response = await $fetch(`${apiUrl}`, {
      method: "POST",
      body: formData,
    });
    data.value = response;
    currentPage.value = 1;
    snackbar.value.message = "Found " + response.length + " items";
    snackbar.value.color = "success";
    snackbar.value.show = true;
  } catch (error) {
    console.error("Error during submission:", error);
    snackbar.value.message = error;
    snackbar.value.color = "error";
    snackbar.value.show = true;
  }
};

const openDialog = (item) => {
  selectedItem.value = item;
  dialog.value = true;
  if (item.type === "pixiv" || item.type === "pixiv1") {
    selectedItem.value.link = `https://www.pixiv.net/artworks/${item.illustid}`;
  } else if (item.type === "twitter") {
    selectedItem.value.link = `https://twitter.com/${item.userid}/status/${item.illustid}`;
  } else if (item.type === "yandere") {
    selectedItem.value.link = `https://yande.re/post/show/${item.id}`;
  }
};

const scrollToTop = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' });
};
</script>
