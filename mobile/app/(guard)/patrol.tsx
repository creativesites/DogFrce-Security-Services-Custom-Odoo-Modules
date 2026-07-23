import React, { useState } from 'react';
import { View, StyleSheet, ScrollView, Alert, Image, TouchableOpacity } from 'react-native';
import { Text, TextInput, Button, Card } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Theme } from '../../src/theme';
import { guardLogPatrol } from '../../src/api/guard';
import * as Location from 'expo-location';
import * as ImagePicker from 'expo-image-picker';

export default function GuardPatrolScreen() {
  const [note, setNote] = useState('');
  const [photoUri, setPhotoUri] = useState<string | null>(null);
  const [photoBase64, setPhotoBase64] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleTakePhoto = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission Denied', 'Camera permission is required to attach patrol photos.');
      return;
    }
    const res = await ImagePicker.launchCameraAsync({
      quality: 0.5,
      base64: true,
      allowsEditing: false,
    });
    if (!res.canceled && res.assets && res.assets[0]) {
      setPhotoUri(res.assets[0].uri);
      setPhotoBase64(res.assets[0].base64 || null);
    }
  };

  const handleSubmitPatrol = async () => {
    if (!note.trim() && !photoBase64) {
      Alert.alert('Empty Log', 'Please type a patrol note or capture a photo.');
      return;
    }

    setSubmitting(true);
    try {
      let locCoords: { latitude: number; longitude: number } | undefined;
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status === 'granted') {
        const currentLoc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
        locCoords = {
          latitude: currentLoc.coords.latitude,
          longitude: currentLoc.coords.longitude,
        };
      }

      const res = await guardLogPatrol(note.trim() || 'Routine Patrol Check-in', locCoords, photoBase64 || undefined);
      Alert.alert('Patrol Recorded', `Patrol check-in #${res.patrol_id} submitted successfully.`);
      setNote('');
      setPhotoUri(null);
      setPhotoBase64(null);
    } catch (err: any) {
      Alert.alert('Patrol Error', err.message || 'Failed to submit patrol log.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Card style={styles.card}>
        <Card.Content style={styles.cardContent}>
          <Text style={styles.title}>Submit Duty / Patrol Log</Text>
          <Text style={styles.subtitle}>
            Log your hourly site checks, perimeter observations, or unusual events.
          </Text>

          <TextInput
            mode="outlined"
            label="Patrol Note / Observations"
            placeholder="e.g. Perimeter fence secure, all locks checked..."
            value={note}
            onChangeText={setNote}
            multiline
            numberOfLines={4}
            style={styles.input}
            outlineColor={Theme.colors.border}
            activeOutlineColor={Theme.colors.primary}
          />

          <View style={styles.photoBox}>
            <Text style={styles.photoLabel}>Photo Evidence (Optional)</Text>
            {photoUri ? (
              <View style={styles.previewWrapper}>
                <Image source={{ uri: photoUri }} style={styles.photoPreview} />
                <TouchableOpacity style={styles.removePhotoBtn} onPress={() => { setPhotoUri(null); setPhotoBase64(null); }}>
                  <MaterialCommunityIcons name="close-circle" size={24} color="#FFF" />
                </TouchableOpacity>
              </View>
            ) : (
              <TouchableOpacity style={styles.addPhotoBtn} onPress={handleTakePhoto}>
                <MaterialCommunityIcons name="camera-plus-outline" size={24} color={Theme.colors.primary} />
                <Text style={styles.addPhotoText}>Take Site Photo</Text>
              </TouchableOpacity>
            )}
          </View>

          <Button
            mode="contained"
            icon="shield-check"
            onPress={handleSubmitPatrol}
            loading={submitting}
            disabled={submitting}
            style={styles.submitBtn}
            labelStyle={styles.submitLabel}
          >
            SUBMIT PATROL CHECK-IN
          </Button>
        </Card.Content>
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Theme.colors.background },
  content: { padding: 16 },
  card: {
    backgroundColor: Theme.colors.surface,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: 16,
    elevation: 0,
  },
  cardContent: { padding: 16, gap: 16 },
  title: { fontSize: 18, fontWeight: '700', color: Theme.colors.text },
  subtitle: { fontSize: 12, color: Theme.colors.placeholder, marginTop: -8 },
  input: { backgroundColor: Theme.colors.surface },
  photoBox: { gap: 8 },
  photoLabel: { fontSize: 13, fontWeight: '600', color: Theme.colors.text },
  addPhotoBtn: {
    borderWidth: 1,
    borderColor: Theme.colors.border,
    borderStyle: 'dashed',
    borderRadius: 12,
    padding: 20,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: `${Theme.colors.primary}05`,
  },
  addPhotoText: { color: Theme.colors.primary, fontSize: 13, fontWeight: '600' },
  previewWrapper: { position: 'relative', borderRadius: 12, overflow: 'hidden' },
  photoPreview: { width: '100%', height: 180, borderRadius: 12 },
  removePhotoBtn: { position: 'absolute', top: 8, right: 8, backgroundColor: 'rgba(0,0,0,0.6)', borderRadius: 12 },
  submitBtn: { backgroundColor: Theme.colors.primary, borderRadius: 12, paddingVertical: 6, marginTop: 8 },
  submitLabel: { fontSize: 14, fontWeight: '800', color: '#FFF' },
});
